#!/usr/bin/env python3
"""Native Linux & Fedora stage adapter for ePlus AI Toolkit with Waydroid support.

Steps 2–5 can request real Google Play charges. The adapter checks the
selected device, current Play account, offer ID and today's introductory
price before invoking the billing flow. It never uses --force or account switching.
"""
from __future__ import annotations

import argparse
import base64
from importlib import metadata
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

from device_selector import auto_select_device, online_serials
from waydroid_helper import connect_waydroid, is_waydroid_installed, is_waydroid_running

ROOT = Path(__file__).resolve().parent
FRIDA_REQUIRED = "16.5.9"
REPORT_DIR = ROOT / "ultra0-report"
EMAIL = re.compile(r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$")
STAGES = {
    2: ("pro12", "12months-eft", False),
    3: ("pro6", "6months-eft", True),
    4: ("pro6b", "6months-eft-2", True),
    5: ("pro6c", "6months-eft-ss-2026", True),
}


def stage_command(step: int, serial: str, account: str = "",
                  python: str = sys.executable) -> list[str]:
    if type(step) is not int or step not in range(6):
        raise ValueError("Step must be an integer between 0 and 5")
    if not serial or serial.startswith("-"):
        raise ValueError("Selected Android device must have an explicit ADB serial")
    base = [python, str(ROOT / "ultra0.py")]
    if step == 0:
        return base + ["--check", "--serial", serial]
    if step == 1:
        return base + ["--list", "--no-add", "--no-switch", "--plan", "pro12",
                       "--account", "current@device", "--serial", serial]
    if not EMAIL.fullmatch(account):
        raise ValueError("A verified Google Play email is required before checkout")
    plan, _offer, stack = STAGES[step]
    result = base + ["--account", account, "--no-add", "--no-switch",
                     "--plan", plan, "--serial", serial]
    if stack:
        result.append("--stack")
    return result


def preflight() -> tuple[str, str]:
    adb = os.environ.get("ADB_PATH") or shutil.which("adb")
    if not adb:
        raise RuntimeError(
            "ADB is missing. On Fedora, install it with: sudo dnf install android-tools"
        )
    try:
        installed = metadata.version("frida")
    except metadata.PackageNotFoundError:
        installed = None
    if installed != FRIDA_REQUIRED:
        raise RuntimeError(
            f"Frida {FRIDA_REQUIRED} required (found {installed or 'none'}). "
            "Use ./run-linux.sh to prepare the local virtual environment."
        )

    devices = online_serials(adb)
    if not devices:
        # Attempt auto-connection to Waydroid
        connect_waydroid(adb)
        devices = online_serials(adb)

    if not devices:
        if is_waydroid_installed() and not is_waydroid_running():
            raise RuntimeError(
                "No online Android device found. Waydroid session is STOPPED.\n"
                "Please start Waydroid session:\n"
                "  waydroid session start\n"
                "  (or launch Waydroid UI from application menu)\n"
                "Then re-run this tool."
            )
        raise RuntimeError(
            "No online Android device. If using Waydroid, ensure it is running and run 'adb devices'."
        )

    serial = auto_select_device(adb, serials=devices)
    if not serial:
        raise RuntimeError("Multiple different Android devices detected. Disconnect extras or specify --serial.")
    return adb, serial


def run_engine(command: list[str], env: dict[str, str]) -> int:
    return subprocess.call(command, cwd=ROOT, env=env)


def read_play_account(serial: str, env: dict[str, str]) -> str:
    """Resolve the Google Play profile without importing Windows setup code."""
    command = [sys.executable, str(ROOT / "scripts/runtime-lookup.py"),
               "play-account", "--serial", serial]
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True,
                            text=True, errors="replace", timeout=60)
    if result.returncode:
        raise RuntimeError("Google Play account lookup failed; no checkout started")
    lines = [line.removeprefix("RUNTIME_RESULT:") for line in result.stdout.splitlines()
             if line.startswith("RUNTIME_RESULT:")]
    if len(lines) != 1:
        raise RuntimeError("Google Play account lookup returned an ambiguous result")
    try:
        account = base64.b64decode(lines[0], validate=True).decode("utf-8").strip().lower()
    except (ValueError, UnicodeError) as error:
        raise RuntimeError("Google Play account lookup returned invalid text") from error
    return account if EMAIL.fullmatch(account) else ""


def fresh_report(filename: str, since_ns: int) -> dict:
    path = REPORT_DIR / filename
    try:
        if path.stat().st_mtime_ns < since_ns:
            raise RuntimeError("The result belongs to an older invocation")
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise RuntimeError("A new matching report was not produced") from error
    if not isinstance(obj, dict) or not isinstance(obj.get("status"), str):
        raise RuntimeError("The result report has an invalid format")
    return obj


def list_offers(serial: str, env: dict[str, str], plan: str = "pro12") -> dict:
    command = stage_command(1, serial)
    if plan != "pro12":
        command[command.index("--plan") + 1] = plan
    start_ns = time.time_ns()
    if run_engine(command, env):
        raise RuntimeError("Google Play offer listing failed; checkout not started")
    report = fresh_report("current.json", start_ns)
    if report["status"] != "listed" or not isinstance(report.get("offers"), list):
        raise RuntimeError("No successful offer listing; checkout not started")
    return report


def verified_account(serial: str, env: dict[str, str], report: dict) -> str:
    before = read_play_account(serial, env)
    listed = str(report.get("detected_play_account") or "").strip().lower()
    if listed and not EMAIL.fullmatch(listed):
        raise RuntimeError("Invalid Google Play account reported during offer listing")
    if before and listed and before != listed:
        raise RuntimeError("Google Play account changed during checks; stop before checkout")
    account = listed or before
    if not account or not EMAIL.fullmatch(account):
        raise RuntimeError("Could not verify Google Play account; no checkout started")
    return account


def check_offer(report: dict, step: int) -> None:
    _plan, expected, _stack = STAGES[step]
    matches = [offer for offer in report["offers"] if isinstance(offer, dict) and
               offer.get("id") == expected and str(offer.get("micros")) == "0"]
    if not matches:
        raise RuntimeError(
            f"Step {step} offer {expected} has no verified zero-priced first phase. "
            "No checkout started."
        )


def run_stage(step: int, serial: str, env: dict[str, str],
              confirmed: bool = False, active_confirmed: bool = False) -> int:
    if step == 0:
        return run_engine(stage_command(0, serial), env)
    if step == 1:
        report = list_offers(serial, env)
        account = verified_account(serial, env, report)
        print(f"Account {account}", flush=True)
        print(f"Offers {len(report['offers'])} (eligibility not guaranteed)", flush=True)
        return 0
    if not confirmed or (step >= 3 and not active_confirmed):
        raise RuntimeError("Explicit checkout and existing-plan confirmations required")
    print("Checking Android environment before paid stage...", flush=True)
    if run_engine(stage_command(0, serial), env):
        raise RuntimeError("Android environment checks failed; no checkout started")
    plan, _offer, _stack = STAGES[step]
    report = list_offers(serial, env, plan)
    account = verified_account(serial, env, report)
    check_offer(report, step)
    # Verify account once again before entering checkout
    if read_play_account(serial, env) != account:
        raise RuntimeError("Google Play account changed; no checkout started")
    print(f"Account {account}", flush=True)
    print(f"Step {step} offer inspected; first phase zero-priced.", flush=True)
    print("CAUTION: Checkout may incur charges. Verify all terms in Google Play.", flush=True)
    return run_engine(stage_command(step, serial, account), env)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ePlus AI Toolkit Linux & Fedora stage adapter (Waydroid)")
    parser.add_argument("--step", type=int, required=True, choices=range(6))
    parser.add_argument("--confirmed", action="store_true",
                        help="Explicitly authorize the selected checkout stage")
    parser.add_argument("--active-confirmed", action="store_true",
                        help="Confirm existing active plan for Steps 3–5")
    args = parser.parse_args(argv)
    if args.step >= 2 and not args.confirmed:
        parser.error("Steps 2–5 require explicit --confirmed; may initiate real charges")
    if args.step >= 3 and not args.active_confirmed:
        parser.error("Steps 3–5 also require --active-confirmed")
    try:
        adb, serial = preflight()
        env = os.environ.copy()
        env["ADB_PATH"] = adb
        env["PYTHONIOENCODING"] = "utf-8:backslashreplace"
        env["PYTHONUTF8"] = "1"
        print(f"Device {serial}", flush=True)
        return run_stage(args.step, serial, env, args.confirmed, args.active_confirmed)
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
        print(f"Stage stopped: {type(error).__name__}: {error}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
