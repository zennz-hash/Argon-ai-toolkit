"""Read-only Google Play SKU/offer inspector for Google One via Frida.

Queries Google Play BillingClient product details in list-only mode without
opening checkout or initiating purchases. Never prints offer or purchase tokens.

Usage:
    python query_sku.py g1.2tb.ai.subs_variant [OTHER_SKUS...]
    python query_sku.py --preset pro --serial 192.168.240.112:5555
    python query_sku.py --preset all --only-free
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import threading
import time

import ultra0

SKU_RE = re.compile(r"^g1\.[A-Za-z0-9._-]{2,120}$")

# Google Play BillingClient caps queryProductDetailsAsync at 20 SKUs per batch.
MAX_BATCH_SIZE = 15

SKU_PRESETS: dict[str, tuple[str, ...]] = {
    "pro": (
        "g1.2tb.ai.subs_variant",
        "g1.2tb.ai.18months_eft",
        "g1.2tb.ai.15months_eft",
        "g1.2tb.ai.12months_eft",
        "g1.play.2tb.ai.student",
        "g1.2tb.ai.6months_eft",
        "g1.2tb.ai.4months_eft",
        "g1.2tb.ai.3months_eft",
        "g1.2tb.ai.2months_eft",
        "g1.play.2tb.ai",
        "g1.2tb.ai",
        "g1.2tb.ai.annual",
        "g1.2tb.ai.12months_ip_90p",
        "g1.2tb.ai.12months_ip_75p",
        "g1.2tb.ai.3months_ip_90p.acq",
        "g1.2tb.ai.3months_ip_50p",
        "g1.2tb.ai.2months_ip_90p.acq",
        "g1.2tb.ai.2months_ip_50p",
        "g1.2tb.ai.1month_ip_95p.acq",
    ),
    "ultra": (
        "g1.20tb.1month_eft.acq",
        "g1.20tb.3months_ip_90p.acq",
        "g1.20tb.3months_ip_80p",
        "g1.20tb.3months_ip_75p.acq",
        "g1.20tb.v2",
        "g1.play.20tb",
        "g1.ai.ultra.1month_eft.acq",
        "g1.ai.ultra.3months_ip_90p.acq",
        "g1.ai.ultra.3months_ip_75p.acq",
        "g1.play.ai.pro",
        "g1.ai.pro",
        "g1.30tb",
        "g1.10tb",
        "g1.5tb",
        "g1.5tb.annual",
    ),
    "plus": (
        "g1.2tb.1year_eft",
        "g1.2tb.6months_eft",
        "g1.2tb.3months_eft",
        "g1.2tb.1month_eft",
        "g1.2tb.annual.3months_eft",
        "g1.2tb.annual.1month_eft",
        "g1.2tb.subs_variant",
        "g1.2tb",
        "g1.2tb.annual",
        "g1.play.helium",
        "g1.play.helium.student",
    ),
    "storage": (
        "g1.100gb",
        "g1.100gb.annual",
        "g1.100gb.1year_eft",
        "g1.100gb.annual.1year_eft",
        "g1.100gb.9months_eft",
        "g1.100gb.180days_eft",
        "g1.100gb.3months_eft",
        "g1.100gb.annual.3months_eft",
        "g1.100gb.2months_eft",
        "g1.100gb.1month_eft",
        "g1.100gb.annual.1month_eft",
        "g1.200gb",
        "g1.200gb.annual",
        "g1.200gb.1year_eft",
        "g1.200gb.180days_eft",
        "g1.200gb.3months_eft",
        "g1.200gb.annual.3months_eft",
        "g1.200gb.1month_eft",
        "g1.200gb.annual.1month_eft",
        "g1.30gb",
        "g1.30gb.annual",
        "g1.30gb.3month_eft",
        "g1.30gb.1month_eft",
        "g1.30gb.annual.1month_eft",
        "g1.youtube_premium_individual_add_on",
    ),
    "discounts": (
        "g1.2tb.ai.12months_ip_90p",
        "g1.2tb.ai.12months_ip_75p",
        "g1.2tb.ai.3months_ip_90p.acq",
        "g1.2tb.ai.3months_ip_50p",
        "g1.2tb.ai.2months_ip_90p.acq",
        "g1.2tb.ai.2months_ip_50p",
        "g1.2tb.ai.1month_ip_95p.acq",
        "g1.2tb.12months_ip.4.99",
        "g1.2tb.6months_ip.4.99",
        "g1.2tb.3months_ip.2.49",
        "g1.2tb.3months_ip_50p",
        "g1.2tb.3months_ip_50p.acq",
        "g1.2tb.3months_ip_80p",
        "g1.2tb.3months_ip_85p.acq",
        "g1.2tb.3months_ip_90p.acq",
        "g1.2tb.2months_ip_50p.acq",
        "g1.2tb.2months_ip_75p",
        "g1.2tb.2months_ip_80p",
        "g1.2tb.1month_ip.2.49",
        "g1.2tb.1month_ip_50p",
        "g1.2tb.1month_ip_80p",
        "g1.2tb.1month_ip_85p.acq",
        "g1.2tb.1month_ip_90p.acq",
        "g1.2tb.1month_ip_95p.acq",
        "g1.2tb.annual.12months_ip_10p",
        "g1.2tb.annual.12months_ip_15p",
        "g1.2tb.annual.12months_ip_20p",
        "g1.2tb.annual.12months_ip_25p.acq",
        "g1.2tb.annual.12months_ip_40p",
        "g1.helium.12months_ip_50p",
        "g1.helium.12months_ip_75p",
        "g1.helium.12months_ip_90p",
        "g1.helium.3months_ip_75p.acq",
        "g1.helium.2months_ip_50p",
        "g1.helium.1month_ip_75p.acq",
        "g1.helium.1month_ip_90p.acq",
        "g1.helium.1month_ip_95p",
        "g1.helium.annual.12months_ip_10p.acq",
        "g1.helium.annual.12months_ip_25p.acq",
        "g1.100gb.12months_ip.0.49",
        "g1.100gb.12months_ip.0.99",
        "g1.100gb.6months_ip.0.99",
        "g1.100gb.6months_ip_75p",
        "g1.100gb.3months_ip_50p",
        "g1.100gb.3months_ip_50p.acq",
        "g1.100gb.3months_ip_85p.acq",
        "g1.100gb.2months_ip_75p",
        "g1.100gb.1month_ip.0.49",
        "g1.100gb.1month_ip.0.99",
        "g1.100gb.1month_ip_50p",
        "g1.100gb.1month_ip_85p.acq",
        "g1.100gb.1month_ip_95p.acq",
        "g1.100gb.annual.12months_ip_10p",
        "g1.100gb.annual.12months_ip_15p",
        "g1.100gb.annual.12months_ip_20p",
        "g1.100gb.annual.12months_ip_40p",
        "g1.200gb.12months_ip.1.49",
        "g1.200gb.6months_ip.1.49",
        "g1.200gb.3months_ip_50p",
        "g1.200gb.3months_ip_50p.acq",
        "g1.200gb.3months_ip_85p.acq",
        "g1.200gb.2months_ip_75p",
        "g1.200gb.1month_ip_50p",
        "g1.200gb.1month_ip_85p.acq",
        "g1.200gb.1month_ip_95p.acq",
        "g1.200gb.annual.12months_ip_10p",
        "g1.200gb.annual.12months_ip_15p",
        "g1.200gb.annual.12months_ip_20p",
        "g1.200gb.annual.12months_ip_40p",
        "g1.30gb.12month_ip_50p",
        "g1.30gb.6month_ip_50p",
        "g1.30gb.3month_ip_75p",
        "g1.30gb.3months_ip_50p.acq",
        "g1.30gb.3months_ip_85p.acq",
        "g1.30gb.1month_ip_75p",
        "g1.30gb.1month_ip_85p.acq",
        "g1.30gb.1month_ip_95p.acq",
        "g1.30gb.annual.1year_ip_10p",
        "g1.30gb.annual.1year_ip_15p",
        "g1.30gb.annual.1year_ip_20p",
        "g1.30gb.annual.1year_ip_40p",
    ),
}

ALL_PRESET_GROUPS = ("pro", "ultra", "plus", "storage", "discounts")


def resolve_skus(explicit: list[str], preset: str | None = None) -> list[str]:
    """Combine preset and explicit SKUs while deduplicating and validating."""
    raw: list[str] = []
    if preset:
        if preset == "all":
            for group in ALL_PRESET_GROUPS:
                raw.extend(SKU_PRESETS[group])
        elif preset in SKU_PRESETS:
            raw.extend(SKU_PRESETS[preset])
        else:
            raise ValueError(f"Unknown SKU preset: {preset}")
    raw.extend(explicit)
    if not raw:
        raw = ["g1.2tb.ai.subs_variant"]

    seen: set[str] = set()
    validated: list[str] = []
    for sku in raw:
        clean = sku.strip()
        if not SKU_RE.fullmatch(clean):
            raise ValueError(f"Invalid Google One SKU format: {sku!r}")
        if clean not in seen:
            seen.add(clean)
            validated.append(clean)
    return validated


def chunk_skus(skus: list[str], size: int = MAX_BATCH_SIZE) -> list[list[str]]:
    """Split SKU queries into BillingClient-safe batches."""
    if size <= 0:
        raise ValueError("Batch size must be positive")
    return [skus[i:i + size] for i in range(0, len(skus), size)]


def build_readonly_query_js(skus: list[str]) -> str:
    """Build a strictly read-only Frida BillingClient query script for SKUs."""
    validated = resolve_skus(skus)
    js = ultra0.build_js("5x", list_only=True)
    target = 'var PRODUCTS=["g1.play.20tb"];'
    if target not in js:
        raise RuntimeError("Could not locate PRODUCTS placeholder in billing script")
    return js.replace(target, f"var PRODUCTS={json.dumps(validated)};", 1)


def sanitize_offer(payload: dict) -> dict:
    """Drop private billing/offer tokens before storing or displaying offer data."""
    return {
        "product": str(payload.get("product") or ""),
        "id": str(payload.get("id") or "null"),
        "micros": str(payload.get("micros") or ""),
        "period": str(payload.get("period") or ""),
        "title": str(payload.get("title") or ""),
        "name": str(payload.get("name") or ""),
        "has_token": bool(payload.get("token")),
    }


def format_price(micros: str) -> str:
    """Format BillingClient priceAmountMicros without assuming USD."""
    if str(micros) == "0":
        return "0 (free intro phase)"
    try:
        amount = int(micros) / 1_000_000
        return f"{amount:,.2f} (local currency)"
    except (TypeError, ValueError):
        return f"{micros} micros"


def query_batch(dev, pid: int, skus: list[str], timeout: float = 25.0) -> tuple[list[dict], list[dict]]:
    """Run one read-only BillingClient query batch on an attached Frida device."""
    js = build_readonly_query_js(skus)
    sess = dev.attach(pid)
    done = threading.Event()
    offers: list[dict] = []
    errors: list[dict] = []

    def on_msg(message, _data):
        if message.get("type") == "error":
            errors.append({"ev": "frida_error", "m": str(message.get("description") or "")[:200]})
            done.set()
            return
        payload = message.get("payload") or {}
        if not isinstance(payload, dict):
            return
        ev = payload.get("ev")
        if ev == "offer":
            offers.append(sanitize_offer(payload))
        elif ev in ("list_only", "no_trial", "query_err", "boot_err"):
            if ev in ("query_err", "boot_err"):
                errors.append({"ev": ev, "m": str(payload.get("m") or "")[:200]})
            done.set()
        elif ev == "pd" and payload.get("code") != 0:
            errors.append({"ev": "pd_error", "code": payload.get("code")})
            done.set()
        elif ev == "pd" and payload.get("n") == 0:
            done.set()

    script = sess.create_script(js)
    script.on("message", on_msg)
    try:
        script.load()
        done.wait(timeout=timeout)
        time.sleep(0.5)
    finally:
        try:
            script.unload()
        except Exception:
            pass
        try:
            sess.detach()
        except Exception:
            pass
    return offers, errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only Google Play SKU inspector for Google One (no checkout)."
    )
    parser.add_argument(
        "skus",
        nargs="*",
        help="Explicit Google One product IDs (e.g. g1.2tb.ai.18months_eft).",
    )
    parser.add_argument(
        "--preset",
        choices=["pro", "ultra", "plus", "storage", "discounts", "all"],
        default=None,
        help="Inspect a curated group of public Google One SKU candidates.",
    )
    parser.add_argument(
        "--serial",
        default=None,
        help="Explicit ADB device serial (required if multiple devices are connected).",
    )
    parser.add_argument(
        "--only-free",
        action="store_true",
        help="Show only offers whose first pricing phase is 0 micros.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=25.0,
        help="Timeout in seconds per BillingClient query batch (default: 25).",
    )
    parser.add_argument(
        "--no-launch",
        action="store_true",
        help="Attach to an already running Google One process without restarting it.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a sanitized JSON summary line (no offer/purchase tokens) for UI clients.",
    )
    return parser


def find_running_google_one_pid() -> int:
    pid_out = ultra0.sh("shell", f"pidof {ultra0.PKG}", timeout=10).strip()
    pids = [int(p) for p in pid_out.split() if p.isdigit()]
    return pids[0] if pids else 0


def maybe_connect_waydroid(adb_path: str) -> None:
    """Connect Waydroid over ADB on Linux if running and not yet attached."""
    if sys.platform != "linux":
        return
    try:
        status = subprocess.run(["waydroid", "status"], capture_output=True, text=True, timeout=5)
        for line in status.stdout.splitlines():
            if "IP address:" in line:
                ip = line.split("IP address:", 1)[1].strip()
                if ip and ip != "UNKNOWN":
                    subprocess.run([adb_path, "connect", f"{ip}:5555"],
                                   capture_output=True, text=True, timeout=6)
                break
    except Exception:
        pass


def format_report(skus: list[str], offers: list[dict], only_free: bool = False) -> str:
    """Format sanitized offer inspection results as human-readable text."""
    free_offers = [o for o in offers if o.get("micros") == "0"]
    paid_offers = [o for o in offers if o.get("micros") != "0"]
    shown = free_offers if only_free else (free_offers + paid_offers)
    unique_products = len({o["product"] for o in shown if o.get("product")})

    lines = [
        f"\n=== Read-only SKU inspection ({len(skus)} SKU(s) queried) ===",
        f"Summary: {len(shown)} offer(s) across {unique_products} SKU(s) "
        f"({len(free_offers)} free intro phase, {0 if only_free else len(paid_offers)} paid/discount)",
    ]
    if not shown:
        lines.append("  (No matching offers were returned)")
    else:
        if free_offers:
            lines.append("\n[Free Introductory Offers (0 micros first phase)]")
            for o in free_offers:
                label = o.get("name") or o.get("title") or ""
                lines.append(
                    f"  {o['product']:34s} offerId={o['id']:22s} "
                    f"{format_price(o.get('micros', '')):24s} period={o['period']:6s} [{label}]"
                )
        if not only_free and paid_offers:
            lines.append("\n[Discounted & Standard Paid Offers]")
            for o in paid_offers:
                label = o.get("name") or o.get("title") or ""
                lines.append(
                    f"  {o['product']:34s} offerId={o['id']:22s} "
                    f"{format_price(o.get('micros', '')):24s} period={o['period']:6s} [{label}]"
                )
    lines.append(
        "\nNote: BillingClient offer metadata is read-only and does NOT guarantee "
        "server-side eligibility, free activation, or Google Play checkout approval."
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    skus = resolve_skus(args.skus, preset=args.preset)

    ultra0.ADB = ultra0.find_adb()
    if not args.serial:
        maybe_connect_waydroid(ultra0.ADB)
    ultra0.pick_device(preferred=args.serial)
    ultra0.ensure_root()
    ultra0.ensure_frida_server()
    ultra0.ensure_module_apk()
    ultra0.ensure_vending()

    pid = find_running_google_one_pid() if args.no_launch else 0
    if not pid:
        pid = ultra0.launch_app()
    if not pid:
        raise SystemExit("Google One process could not be started on the Android target.")

    dev = ultra0.get_target_frida_device(pid, ultra0.SERIAL)
    all_offers: list[dict] = []
    all_errors: list[dict] = []

    batches = chunk_skus(skus)
    for idx, batch in enumerate(batches, 1):
        print(f"Querying SKU batch {idx}/{len(batches)} ({len(batch)} SKUs)...", flush=True)
        batch_offers, batch_errors = query_batch(dev, pid, batch, timeout=args.timeout)
        all_offers.extend(batch_offers)
        all_errors.extend(batch_errors)

    print(format_report(skus, all_offers, only_free=args.only_free), flush=True)
    if args.json:
        filtered = [o for o in all_offers if (not args.only_free or o.get("micros") == "0")]
        payload = {
            "queried_count": len(skus),
            "only_free": bool(args.only_free),
            "offers": [sanitize_offer(o) for o in filtered],
            "errors": all_errors,
        }
        print("SKU_JSON_RESULT:" + json.dumps(payload, ensure_ascii=True), flush=True)
    if all_errors:
        print(f"\nDiagnostics ({len(all_errors)} warning/error event(s)): {all_errors}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
