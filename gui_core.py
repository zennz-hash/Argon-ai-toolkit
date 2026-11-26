"""Pure logic, guided step metadata, and sanitized subprocess helpers for the desktop GUI.

This module never initiates a Google Play checkout or imports Qt.
All Android, Frida, account, and billing actions delegate to existing CLI entrypoints.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

import tui_core

EMAIL_RE = re.compile(r"\b([A-Za-z0-9._%+\-]+)@([A-Za-z0-9.\-]+\.[A-Za-z]{2,})\b")
TOKEN_FIELD_RE = re.compile(r'(["\']?(?:offer_?token|purchase_?token|token)["\']?\s*[:=]\s*["\']?)([A-Za-z0-9+/=._-]{16,})(["\']?)', re.I)
SKU_RE = re.compile(r"^g1\.[A-Za-z0-9._-]{2,120}$")
OFFER_RE = re.compile(r"^[A-Za-z0-9._-]{1,80}$")

PERIOD_MONTHS = {
    "P1Y6M": 18,
    "P18M": 18,
    "P1Y3M": 15,
    "P15M": 15,
    "P1Y": 12,
    "P12M": 12,
    "P52W1D": 12,
    "P9M": 9,
    "P6M": 6,
    "P26W2D": 6,
    "P180D": 6,
    "P4M": 4,
    "P3M": 3,
    "P13W1D": 3,
    "P2M": 2,
    "P8W6D": 2,
    "P1M": 1,
    "P4W3D": 1,
}

PERIOD_LABELS = {
    "P1Y6M": "18 bulan",
    "P18M": "18 bulan",
    "P1Y3M": "15 bulan",
    "P15M": "15 bulan",
    "P1Y": "12 bulan",
    "P12M": "12 bulan",
    "P52W1D": "12 bulan",
    "P9M": "9 bulan",
    "P6M": "6 bulan",
    "P26W2D": "6 bulan",
    "P180D": "180 hari",
    "P4M": "4 bulan",
    "P3M": "3 bulan",
    "P13W1D": "3 bulan",
    "P2M": "2 bulan",
    "P8W6D": "2 bulan",
    "P1M": "1 bulan",
    "P4W3D": "1 bulan",
}

SKU_PRESET_CHOICES = (
    ("pro", "Google AI Pro (5 TB)"),
    ("ultra", "Google AI Ultra (20 TB / 30 TB)"),
    ("plus", "Google AI Plus (2 TB / 400 GB)"),
    ("storage", "Penyimpanan (30 GB / 100 GB / 200 GB)"),
    ("discounts", "Penawaran Diskon"),
    ("all", "Semua Katalog (130+ SKU)"),
)


@dataclass(frozen=True)
class GuidedStep:
    key: str
    badge: str
    title: str
    subtitle: str
    is_checkout: bool
    requires_active_plan: bool
    default_no_tap: bool
    product_id: str
    offer_id: str
    cta_label: str
    summary: str
    checklist: tuple[str, ...]
    safety_note: str


GUIDED_STEPS: tuple[GuidedStep, ...] = (
    GuidedStep(
        key="step0",
        badge="Step 0",
        title="Cek Lingkungan & Waydroid",
        subtitle="Verifikasi ADB, root Waydroid, Frida 16.5.9, dan Google Play",
        is_checkout=False,
        requires_active_plan=False,
        default_no_tap=False,
        product_id="",
        offer_id="",
        cta_label="Jalankan Step 0: Cek Lingkungan",
        summary=(
            "Memeriksa apakah Waydroid aktif, tersambung ke ADB, memiliki akses root, "
            "dan frida-server 16.5.9 siap digunakan."
        ),
        checklist=(
            "Pastikan sesi Waydroid sudah berjalan (bisa dibuka lewat tombol Buka Waydroid UI).",
            "Pastikan Google Play Store dan Google One sudah terpasang serta login ke akun yang dituju.",
            "Step ini tidak membuka checkout, tetapi dapat memulai atau menyiapkan frida-server di Waydroid.",
        ),
        safety_note="Aman dari penagihan: tidak membuka halaman pembayaran Google Play.",
    ),
    GuidedStep(
        key="step1",
        badge="Step 1",
        title="Cek Akun & Offer Standar",
        subtitle="Baca akun Play aktif dan daftar offer Pro standar (Read-Only)",
        is_checkout=False,
        requires_active_plan=False,
        default_no_tap=False,
        product_id="g1.2tb.ai.subs_variant",
        offer_id="",
        cta_label="Jalankan Step 1: Cek Akun & Offer",
        summary=(
            "Mendeteksi akun Google Play yang sedang aktif di Waydroid dan membaca metadata "
            "offer Google AI Pro tanpa membuka checkout."
        ),
        checklist=(
            "Pastikan akun yang tampil di Google Play Store adalah akun yang benar.",
            "Untuk memindai 130+ SKU (termasuk 18 bulan, 15 bulan, Ultra), gunakan tab Deteksi Offer.",
            "Metadata offer yang tampil bersifat read-only dan bukan jaminan kelayakan server.",
        ),
        safety_note="Read-Only: hanya membaca informasi akun dan daftar offer, tanpa transaksi.",
    ),
    GuidedStep(
        key="pro18",
        badge="Pro 18B",
        title="Checkout Pro 18 Bulan (Tinjau Manual)",
        subtitle="SKU g1.2tb.ai.18months_eft (offer eft-18months, 18 bulan)",
        is_checkout=True,
        requires_active_plan=False,
        default_no_tap=True,
        product_id="g1.2tb.ai.18months_eft",
        offer_id="eft-18months",
        cta_label="Buka Checkout 18 Bulan (Tinjau Manual)",
        summary=(
            "Memverifikasi akun Google Play aktif dan offer eft-18months berharga 0 pada fase awal, "
            "lalu membuka sheet checkout Google Play di Waydroid agar Anda meninjau sendiri."
        ),
        checklist=(
            "Sebelum lanjut, cek tab Deteksi Offer dan pastikan g1.2tb.ai.18months_eft (eft-18months) muncul.",
            "Mode Tinjau Manual (--no-tap) aktif secara default agar tombol Subscribe tidak diklik otomatis.",
            "Di jendela Waydroid, periksa harga hari ini Rp 0, durasi 18 bulan, metode bayar, dan tarif perpanjangan.",
            "Tekan Langganan / Subscribe secara manual hanya jika seluruh ketentuan di Google Play sesuai.",
        ),
        safety_note=(
            "Berpotensi tagihan nyata: selalu periksa nominal hari ini dan tanggal perpanjangan "
            "langsung di jendela Google Play sebelum menyetujui."
        ),
    ),
    GuidedStep(
        key="step2",
        badge="Step 2",
        title="Pro 12 Bulan (Standar)",
        subtitle="SKU g1.2tb.ai.subs_variant (offer 12months-eft)",
        is_checkout=True,
        requires_active_plan=False,
        default_no_tap=True,
        product_id="g1.2tb.ai.subs_variant",
        offer_id="12months-eft",
        cta_label="Jalankan Step 2: Pro 12 Bulan",
        summary=(
            "Membuka alur checkout untuk paket dasar Google AI Pro 12 bulan (12months-eft) "
            "setelah verifikasi akun Play Store dan fase awal 0."
        ),
        checklist=(
            "Jalankan Step 1 terlebih dahulu untuk memastikan akun dan offer terdeteksi.",
            "Periksa layar checkout Google Play di Waydroid untuk memastikan harga hari ini 0 dan durasi 12 bulan.",
            "Setelah selesai, buka Google Play -> Pembayaran & langganan -> Langganan untuk verifikasi status aktif.",
        ),
        safety_note=(
            "Berpotensi tagihan nyata: memerlukan konfirmasi eksplisit. Jangan gunakan bila akun sudah berlangganan paket yang sama."
        ),
    ),
    GuidedStep(
        key="step3",
        badge="Step 3",
        title="Pro +6 Bulan (Pertama)",
        subtitle="Pembaruan langganan offer 6months-eft",
        is_checkout=True,
        requires_active_plan=True,
        default_no_tap=True,
        product_id="g1.2tb.ai.subs_variant",
        offer_id="6months-eft",
        cta_label="Jalankan Step 3: Pro +6 Bulan",
        summary=(
            "Membuka pembaruan langganan untuk offer 6months-eft memakai token langganan aktif "
            "yang dibaca langsung dari Google Play."
        ),
        checklist=(
            "Pastikan Step 2 sudah aktif dan tanggal perpanjangannya terlihat di Google Play Subscriptions.",
            "Periksa ketentuan pembaruan di layar Google Play sebelum menekan Subscribe.",
            "Ketentuan perpanjangan akhir sepenuhnya ditentukan oleh server Google Play.",
        ),
        safety_note=(
            "Berpotensi tagihan nyata: wajib verifikasi langganan aktif di Google Play sebelum melanjutkan."
        ),
    ),
    GuidedStep(
        key="step4",
        badge="Step 4",
        title="Pro +6 Bulan (Kedua)",
        subtitle="Pembaruan langganan offer 6months-eft-2",
        is_checkout=True,
        requires_active_plan=True,
        default_no_tap=True,
        product_id="g1.2tb.ai.subs_variant",
        offer_id="6months-eft-2",
        cta_label="Jalankan Step 4: Pro +6 Bulan Kedua",
        summary=(
            "Membuka pembaruan langganan untuk offer 6months-eft-2 setelah verifikasi Step 3 di Google Play."
        ),
        checklist=(
            "Pastikan hasil Step 3 sudah muncul dan tanggal perpanjangan sudah diperbarui di Google Play.",
            "Hentikan proses jika Google Play menampilkan peringatan keamanan akun (OR-REH-04) atau sudah berlangganan.",
        ),
        safety_note=(
            "Berpotensi tagihan nyata: wajib verifikasi langganan aktif dan tanggal perpanjangan di Google Play."
        ),
    ),
    GuidedStep(
        key="step5",
        badge="Step 5",
        title="Opsional +6 Bulan",
        subtitle="Pembaruan langganan offer 6months-eft-ss-2026",
        is_checkout=True,
        requires_active_plan=True,
        default_no_tap=True,
        product_id="g1.2tb.ai.subs_variant",
        offer_id="6months-eft-ss-2026",
        cta_label="Jalankan Step 5: Opsional +6 Bulan",
        summary=(
            "Tahap opsional untuk offer 6months-eft-ss-2026 jika tersedia pada akun dan wilayah Anda."
        ),
        checklist=(
            "Pastikan Step 4 sudah terverifikasi di Google Play Subscriptions.",
            "Jika offer tidak muncul pada akun Anda, proses akan berhenti aman tanpa membuka checkout.",
        ),
        safety_note=(
            "Berpotensi tagihan nyata: wajib verifikasi langganan aktif di Google Play sebelum melanjutkan."
        ),
    ),
)

STEP_BY_KEY = {step.key: step for step in GUIDED_STEPS}


@dataclass(frozen=True)
class OfferRow:
    product: str
    offer_id: str
    micros: str
    period: str
    title: str
    name: str

    @property
    def is_free_intro(self) -> bool:
        return str(self.micros) == "0"

    @property
    def period_months(self) -> int:
        return PERIOD_MONTHS.get(self.period, 0)

    @property
    def period_human(self) -> str:
        return PERIOD_LABELS.get(self.period, self.period or "-")

    @property
    def price_human(self) -> str:
        if self.is_free_intro:
            return "Gratis (0)"
        try:
            amount = int(self.micros) / 1_000_000
            return f"{amount:,.0f}"
        except (TypeError, ValueError):
            return self.micros or "-"

    @property
    def guided_step_key(self) -> str | None:
        if not self.is_free_intro:
            return None
        if self.product == "g1.2tb.ai.18months_eft" and self.offer_id == "eft-18months":
            return "pro18"
        if self.product == "g1.2tb.ai.subs_variant":
            mapping = {
                "12months-eft": "step2",
                "6months-eft": "step3",
                "6months-eft-2": "step4",
                "6months-eft-ss-2026": "step5",
            }
            return mapping.get(self.offer_id)
        return None

    @property
    def is_stack_step(self) -> bool:
        return self.guided_step_key in ("step3", "step4", "step5")

    @property
    def can_open_checkout(self) -> bool:
        """Any detected zero-priced introductory offer with valid SKU and offer ID."""
        if not self.is_free_intro:
            return False
        if not SKU_RE.fullmatch(self.product.strip()):
            return False
        clean_offer = self.offer_id.strip()
        if not clean_offer or clean_offer.lower() == "null":
            return False
        return bool(OFFER_RE.fullmatch(clean_offer))


@dataclass(frozen=True)
class EnvironmentSnapshot:
    waydroid_state: str
    waydroid_ip: str
    adb_serial: str
    adb_available: bool
    venv_ready: bool


def resolve_engine_python(repo: Path) -> str:
    """Prefer the project virtual environment that holds frida 16.5.9."""
    venv_py = repo / ".venv" / "bin" / "python"
    if venv_py.is_file():
        return str(venv_py)
    return sys.executable


def sanitize_log_line(line: str) -> str:
    """Mask email addresses and redact token-like payloads before UI display."""
    def _mask(match: re.Match[str]) -> str:
        name, domain = match.group(1), match.group(2)
        if name.lower() == "current" and domain.lower() == "device":
            return "current@device"
        prefix = name[:2] if len(name) > 2 else name[:1]
        return f"{prefix}***@{domain}"

    cleaned = EMAIL_RE.sub(_mask, line)
    cleaned = TOKEN_FIELD_RE.sub(r"\1[REDACTED]\3", cleaned)
    return cleaned


def build_step_command(
    step_key: str,
    repo: Path,
    confirmed: bool = False,
    active_confirmed: bool = False,
    no_tap: bool = True,
) -> list[str]:
    """Construct the exact linux_runner.py command for a guided step."""
    if step_key not in STEP_BY_KEY:
        raise ValueError(f"Unknown guided step: {step_key}")
    step = STEP_BY_KEY[step_key]
    python = resolve_engine_python(repo)
    runner = repo / "linux_runner.py"
    if not runner.is_file():
        raise FileNotFoundError(f"linux_runner.py not found in {repo}")

    if step_key == "step0":
        return [python, str(runner), "--step", "0"]
    if step_key == "step1":
        return [python, str(runner), "--step", "1"]

    if step.is_checkout and not confirmed:
        raise ValueError(f"Explicit checkout confirmation is required for {step_key}")
    if step.requires_active_plan and not active_confirmed:
        raise ValueError(f"Active Google Play subscription confirmation is required for {step_key}")

    if step_key == "pro18":
        cmd = [python, str(runner), "--pro18", "--confirmed"]
        if no_tap:
            cmd.append("--no-tap")
        return cmd

    step_num = int(step_key.removeprefix("step"))
    cmd = [python, str(runner), "--step", str(step_num), "--confirmed"]
    if step.requires_active_plan:
        cmd.append("--active-confirmed")
    if no_tap:
        cmd.append("--no-tap")
    return cmd


def build_custom_offer_command(
    product: str,
    offer_id: str,
    repo: Path,
    confirmed: bool = False,
) -> list[str]:
    """Construct the manual-review checkout command for any zero-priced catalog offer."""
    if not confirmed:
        raise ValueError("Explicit checkout confirmation is required before opening catalog checkout")
    clean_prod = product.strip()
    clean_offer = offer_id.strip()
    if not SKU_RE.fullmatch(clean_prod):
        raise ValueError(f"Invalid Google One SKU format: {product!r}")
    if not clean_offer or clean_offer.lower() == "null" or not OFFER_RE.fullmatch(clean_offer):
        raise ValueError(f"Invalid zero-priced offer ID: {offer_id!r}")
    python = resolve_engine_python(repo)
    runner = repo / "linux_runner.py"
    if not runner.is_file():
        raise FileNotFoundError(f"linux_runner.py not found in {repo}")
    return [
        python,
        str(runner),
        "--product",
        clean_prod,
        "--offer",
        clean_offer,
        "--confirmed",
        "--no-tap",
    ]


def build_sku_scan_command(
    repo: Path,
    preset: str = "pro",
    only_free: bool = False,
    serial: str = "",
) -> list[str]:
    """Construct the strictly read-only query_sku.py command with JSON output."""
    valid_presets = {key for key, _label in SKU_PRESET_CHOICES}
    if preset not in valid_presets:
        raise ValueError(f"Unknown SKU preset: {preset}")
    python = resolve_engine_python(repo)
    script = repo / "query_sku.py"
    if not script.is_file():
        raise FileNotFoundError(f"query_sku.py not found in {repo}")
    cmd = [python, str(script), "--preset", preset, "--json"]
    if only_free:
        cmd.append("--only-free")
    if serial.strip():
        cmd.extend(["--serial", serial.strip()])
    return cmd


def parse_sku_json_output(output: str) -> tuple[list[OfferRow], int, list[dict]]:
    """Extract sanitized OfferRow objects from query_sku.py --json output."""
    json_lines = [
        line.removeprefix("SKU_JSON_RESULT:").strip()
        for line in output.splitlines()
        if line.startswith("SKU_JSON_RESULT:")
    ]
    if not json_lines:
        return [], 0, []
    try:
        payload = json.loads(json_lines[-1])
    except ValueError:
        return [], 0, []
    raw_offers = payload.get("offers")
    if not isinstance(raw_offers, list):
        raw_offers = []
    rows: list[OfferRow] = []
    for item in raw_offers:
        if not isinstance(item, dict):
            continue
        rows.append(
            OfferRow(
                product=str(item.get("product") or ""),
                offer_id=str(item.get("id") or "null"),
                micros=str(item.get("micros") or ""),
                period=str(item.get("period") or ""),
                title=str(item.get("title") or ""),
                name=str(item.get("name") or ""),
            )
        )
    rows.sort(key=lambda r: (0 if r.is_free_intro else 1, -r.period_months, r.product, r.offer_id))
    queried = int(payload.get("queried_count") or 0)
    errors = payload.get("errors") if isinstance(payload.get("errors"), list) else []
    return rows, queried, errors


def filter_offers(rows: list[OfferRow], query: str = "", only_free: bool = False) -> list[OfferRow]:
    """Filter detected offers by free-intro status and search text."""
    needle = query.strip().lower()
    result: list[OfferRow] = []
    for row in rows:
        if only_free and not row.is_free_intro:
            continue
        if needle:
            haystack = " ".join((row.product, row.offer_id, row.name, row.title, row.period_human)).lower()
            if needle not in haystack:
                continue
        result.append(row)
    return result


def detect_environment_snapshot(repo: Path) -> EnvironmentSnapshot:
    """Lightweight read-only status check for Waydroid, ADB, and venv (no Frida)."""
    waydroid_state = "Tidak terpasang"
    waydroid_ip = ""
    if shutil.which("waydroid"):
        try:
            proc = subprocess.run(
                ["waydroid", "status"],
                capture_output=True,
                text=True,
                timeout=4,
            )
            session = ""
            container = ""
            for line in proc.stdout.splitlines():
                if "Session:" in line:
                    session = line.split("Session:", 1)[1].strip()
                elif "Container:" in line:
                    container = line.split("Container:", 1)[1].strip()
                elif "IP address:" in line:
                    ip_val = line.split("IP address:", 1)[1].strip()
                    if ip_val and ip_val != "UNKNOWN":
                        waydroid_ip = ip_val
            if session.upper() == "RUNNING":
                waydroid_state = "Aktif"
            elif container.upper() == "RUNNING":
                waydroid_state = "Container aktif"
            else:
                waydroid_state = "Berhenti"
        except (OSError, subprocess.SubprocessError):
            waydroid_state = "Tidak diketahui"

    adb_path = shutil.which("adb")
    adb_serial = ""
    if adb_path:
        try:
            if waydroid_ip:
                subprocess.run(
                    [adb_path, "connect", f"{waydroid_ip}:5555"],
                    capture_output=True,
                    text=True,
                    timeout=4,
                )
            proc = subprocess.run(
                [adb_path, "devices"],
                capture_output=True,
                text=True,
                timeout=4,
            )
            for line in proc.stdout.splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "device":
                    adb_serial = parts[0]
                    break
        except (OSError, subprocess.SubprocessError):
            adb_serial = ""

    venv_ready = (repo / ".venv" / "bin" / "python").is_file()
    return EnvironmentSnapshot(
        waydroid_state=waydroid_state,
        waydroid_ip=waydroid_ip,
        adb_serial=adb_serial,
        adb_available=bool(adb_path),
        venv_ready=venv_ready,
    )


def summarize_step_result(step_key: str, exit_code: int, started_at: float, repo: Path,
                          detected_account: str = "") -> tuple[str, str, str]:
    """Return (level, title, guidance) for a finished guided step."""
    if step_key == "step0":
        if exit_code == 0:
            return (
                "ok",
                "Lingkungan Android & Waydroid siap",
                "Lanjutkan ke Step 1 untuk mengecek akun Google Play atau buka tab Deteksi Offer.",
            )
        return (
            "error",
            "Pemeriksaan lingkungan belum selesai",
            "Buka tab Log & Diagnostik untuk melihat penyebabnya. Pastikan Waydroid aktif dan ADB tersambung.",
        )

    if step_key == "step1":
        report = tui_core.read_fresh_report(repo / "ultra0-report", 1, started_at)
        outcome = tui_core.outcome_for_stage(1, exit_code, report)
        if exit_code == 0 and report and report.get("status") == "listed":
            count = len(report.get("offers") or [])
            return (
                "ok",
                f"Offer standar terbaca ({count} offer)",
                "Metadata offer bersifat read-only dan bukan jaminan kelayakan. Anda bisa cek 130+ SKU di tab Deteksi Offer.",
            )
        return ("error", outcome.title, outcome.instruction)

    if exit_code != 0:
        return (
            "error",
            "Tahap berhenti sebelum selesai",
            "Periksa tab Log & Diagnostik serta layar Waydroid sebelum mencoba lagi.",
        )

    if step_key == "pro18":
        return (
            "warn",
            "Sheet checkout 18 bulan sudah diproses",
            "Periksa jendela Google Play di Waydroid: pastikan total hari ini Rp 0, durasi 18 bulan, "
            "dan cek status langganan di Google Play Subscriptions setelah menyetujui.",
        )

    step_num = int(step_key.removeprefix("step"))
    report = tui_core.read_fresh_report(
        repo / "ultra0-report", step_num, started_at, expected_account=detected_account or None
    )
    if report is None:
        return (
            "warn",
            "Perlu pemeriksaan di Google Play",
            "Periksa jendela Waydroid dan halaman Langganan Google Play untuk memastikan status terbaru.",
        )
    outcome = tui_core.outcome_for_stage(step_num, exit_code, report)
    level = "warn" if outcome.can_review or outcome.code in ("checkout_not_confirmed", "awaiting_manual_confirmation") else "error"
    return (level, outcome.title, outcome.instruction)
