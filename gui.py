#!/usr/bin/env python3
"""Native Linux Desktop GUI for ePlus AI Toolkit (PyQt5).

Provides a guided step-by-step workflow and a read-only Google Play offer detector
on top of the existing CLI engine (linux_runner.py, query_sku.py, ultra0.py).
No checkout is ever started automatically.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

from PyQt5 import QtCore, QtGui, QtWidgets

import gui_core

ROOT = Path(__file__).resolve().parent
ICON_PATH = ROOT / "assets" / "argon-ai-toolkit.svg"
ACCOUNT_LINE_RE = re.compile(r"^Account\s+([^\s]+@[^\s]+)$")

LIGHT_PALETTE = {
    "ground": "#F6F7F9",
    "rail": "#ECEFF3",
    "surface": "#FFFFFF",
    "surface_alt": "#F1F4F8",
    "border": "#CBD5E1",
    "control_border": "#6B7280",
    "ink": "#111827",
    "muted": "#4B5563",
    "accent": "#0F766E",
    "accent_hover": "#115E59",
    "accent_ink": "#FFFFFF",
    "accent_tint": "#CCFBF1",
    "accent_tint_ink": "#065F46",
    "ok_bg": "#D1FAE5",
    "ok_ink": "#065F46",
    "warn_bg": "#FEF3C7",
    "warn_ink": "#92400E",
    "danger_bg": "#FEE2E2",
    "danger_ink": "#991B1B",
    "log_bg": "#FFFFFF",
    "log_ink": "#111827",
}

DARK_PALETTE = {
    "ground": "#0F1419",
    "rail": "#131A22",
    "surface": "#181F27",
    "surface_alt": "#1E2732",
    "border": "#2E3A48",
    "control_border": "#7C8DA3",
    "ink": "#F1F5F9",
    "muted": "#94A3B8",
    "accent": "#2DD4BF",
    "accent_hover": "#5EEAD4",
    "accent_ink": "#042F2E",
    "accent_tint": "#133A36",
    "accent_tint_ink": "#A7F3D0",
    "ok_bg": "#064E3B",
    "ok_ink": "#A7F3D0",
    "warn_bg": "#451A03",
    "warn_ink": "#FDE68A",
    "danger_bg": "#450A0A",
    "danger_ink": "#FECACA",
    "log_bg": "#11171E",
    "log_ink": "#F1F5F9",
}


def build_stylesheet(theme: str) -> str:
    p = DARK_PALETTE if theme == "dark" else LIGHT_PALETTE
    return f"""
    QMainWindow, QDialog {{
        background-color: {p['ground']};
        color: {p['ink']};
        font-family: "Inter", "Noto Sans", "Cantarell", sans-serif;
        font-size: 10pt;
    }}
    QWidget {{
        color: {p['ink']};
        font-family: "Inter", "Noto Sans", "Cantarell", sans-serif;
    }}
    QFrame#NavRail {{
        background-color: {p['rail']};
        border-right: 1px solid {p['border']};
    }}
    QFrame#Card, QFrame#DetailCard, QFrame#StatusStrip {{
        background-color: {p['surface']};
        border: 1px solid {p['border']};
        border-radius: 10px;
    }}
    QFrame#EnvCard {{
        background-color: {p['surface']};
        border: 1px solid {p['border']};
        border-radius: 8px;
    }}
    QLabel#AppTitle {{
        font-size: 13pt;
        font-weight: 700;
        color: {p['ink']};
    }}
    QLabel#PageTitle {{
        font-size: 16pt;
        font-weight: 700;
        color: {p['ink']};
    }}
    QLabel#SectionTitle {{
        font-size: 11.5pt;
        font-weight: 600;
        color: {p['ink']};
    }}
    QLabel#Muted {{
        color: {p['muted']};
        font-size: 9.5pt;
    }}
    QLabel#MonoMeta {{
        font-family: "JetBrains Mono", "Fira Code", "Noto Sans Mono", monospace;
        font-size: 9.5pt;
        color: {p['ink']};
        background-color: {p['surface_alt']};
        border: 1px solid {p['border']};
        border-radius: 6px;
        padding: 6px 10px;
    }}
    QLabel#BadgeOk {{
        background-color: {p['ok_bg']};
        color: {p['ok_ink']};
        border-radius: 6px;
        padding: 3px 8px;
        font-weight: 600;
        font-size: 9pt;
    }}
    QLabel#BadgeWarn {{
        background-color: {p['warn_bg']};
        color: {p['warn_ink']};
        border-radius: 6px;
        padding: 3px 8px;
        font-weight: 600;
        font-size: 9pt;
    }}
    QLabel#BadgeDanger {{
        background-color: {p['danger_bg']};
        color: {p['danger_ink']};
        border-radius: 6px;
        padding: 3px 8px;
        font-weight: 600;
        font-size: 9pt;
    }}
    QLabel#BadgeNeutral {{
        background-color: {p['surface_alt']};
        color: {p['muted']};
        border: 1px solid {p['border']};
        border-radius: 6px;
        padding: 3px 8px;
        font-weight: 600;
        font-size: 9pt;
    }}
    QFrame#NoticeWarn {{
        background-color: {p['warn_bg']};
        border: 1px solid {p['warn_ink']};
        border-radius: 8px;
    }}
    QFrame#NoticeWarn QLabel {{
        color: {p['warn_ink']};
    }}
    QFrame#NoticeOk {{
        background-color: {p['ok_bg']};
        border: 1px solid {p['ok_ink']};
        border-radius: 8px;
    }}
    QFrame#NoticeOk QLabel {{
        color: {p['ok_ink']};
    }}
    QFrame#NoticeDanger {{
        background-color: {p['danger_bg']};
        border: 1px solid {p['danger_ink']};
        border-radius: 8px;
    }}
    QFrame#NoticeDanger QLabel {{
        color: {p['danger_ink']};
    }}
    QFrame#NoticeNeutral {{
        background-color: {p['surface_alt']};
        border: 1px solid {p['border']};
        border-radius: 8px;
    }}
    QPushButton#NavButton {{
        text-align: left;
        padding: 10px 12px;
        border-radius: 8px;
        border: 1px solid transparent;
        background-color: transparent;
        color: {p['ink']};
        font-weight: 500;
    }}
    QPushButton#NavButton:hover {{
        background-color: {p['surface']};
        border-color: {p['border']};
    }}
    QPushButton#NavButton[active="true"] {{
        background-color: {p['accent_tint']};
        color: {p['accent_tint_ink']};
        border: 1px solid {p['accent']};
        font-weight: 700;
    }}
    QPushButton#NavButton:focus {{
        border: 2px solid {p['accent']};
    }}
    QPushButton#PrimaryButton {{
        background-color: {p['accent']};
        color: {p['accent_ink']};
        border: 1px solid {p['accent']};
        border-radius: 8px;
        padding: 10px 16px;
        font-weight: 600;
        font-size: 10pt;
    }}
    QPushButton#PrimaryButton:hover {{
        background-color: {p['accent_hover']};
        border-color: {p['accent_hover']};
    }}
    QPushButton#PrimaryButton:focus {{
        border: 2px solid {p['ink']};
    }}
    QPushButton#PrimaryButton:disabled {{
        background-color: {p['surface_alt']};
        color: {p['muted']};
        border-color: {p['border']};
    }}
    QPushButton#SecondaryButton {{
        background-color: {p['surface']};
        color: {p['ink']};
        border: 1px solid {p['control_border']};
        border-radius: 8px;
        padding: 8px 14px;
        font-weight: 500;
    }}
    QPushButton#SecondaryButton:hover {{
        background-color: {p['surface_alt']};
        border-color: {p['accent']};
    }}
    QPushButton#SecondaryButton:focus {{
        border: 2px solid {p['accent']};
    }}
    QPushButton#SecondaryButton:disabled {{
        color: {p['muted']};
        border-color: {p['border']};
        background-color: {p['surface_alt']};
    }}
    QPushButton#DangerButton {{
        background-color: {p['danger_bg']};
        color: {p['danger_ink']};
        border: 1px solid {p['danger_ink']};
        border-radius: 8px;
        padding: 8px 14px;
        font-weight: 600;
    }}
    QPushButton#DangerButton:hover {{
        background-color: {p['danger_ink']};
        color: #FFFFFF;
    }}
    QPushButton#DangerButton:disabled {{
        background-color: {p['surface_alt']};
        color: {p['muted']};
        border-color: {p['border']};
    }}
    QPushButton#StepItem {{
        text-align: left;
        padding: 10px 12px;
        border-radius: 8px;
        border: 1px solid {p['border']};
        background-color: {p['surface']};
        color: {p['ink']};
    }}
    QPushButton#StepItem:hover {{
        background-color: {p['surface_alt']};
        border-color: {p['control_border']};
    }}
    QPushButton#StepItem[selected="true"] {{
        border: 2px solid {p['accent']};
        background-color: {p['surface_alt']};
    }}
    QPushButton#StepItem:focus {{
        border: 2px solid {p['accent']};
    }}
    QComboBox, QLineEdit {{
        background-color: {p['surface']};
        color: {p['ink']};
        border: 1px solid {p['control_border']};
        border-radius: 6px;
        padding: 7px 10px;
        min-height: 20px;
    }}
    QComboBox:focus, QLineEdit:focus {{
        border: 2px solid {p['accent']};
    }}
    QComboBox QAbstractItemView {{
        background-color: {p['surface']};
        color: {p['ink']};
        selection-background-color: {p['accent_tint']};
        selection-color: {p['accent_tint_ink']};
        border: 1px solid {p['border']};
    }}
    QCheckBox {{
        spacing: 8px;
        color: {p['ink']};
    }}
    QCheckBox:focus {{
        color: {p['accent']};
    }}
    QTableWidget {{
        background-color: {p['surface']};
        color: {p['ink']};
        border: 1px solid {p['border']};
        border-radius: 8px;
        gridline-color: {p['border']};
        selection-background-color: {p['accent_tint']};
        selection-color: {p['accent_tint_ink']};
    }}
    QHeaderView::section {{
        background-color: {p['surface_alt']};
        color: {p['ink']};
        border: none;
        border-bottom: 1px solid {p['border']};
        border-right: 1px solid {p['border']};
        padding: 8px 10px;
        font-weight: 600;
        text-align: left;
    }}
    QPlainTextEdit#LogView {{
        background-color: {p['log_bg']};
        color: {p['log_ink']};
        border: 1px solid {p['border']};
        border-radius: 8px;
        font-family: "JetBrains Mono", "Fira Code", "Noto Sans Mono", monospace;
        font-size: 9.5pt;
        padding: 10px;
    }}
    QScrollArea {{
        border: none;
        background-color: transparent;
    }}
    QScrollArea > QWidget > QWidget {{
        background-color: transparent;
    }}
    QScrollBar:vertical {{
        background: {p['ground']};
        width: 8px;
        margin: 2px 0 2px 0;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical {{
        background: {p['border']};
        min-height: 28px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {p['control_border']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: transparent;
        height: 0px;
    }}
    QScrollBar:horizontal {{
        background: {p['ground']};
        height: 8px;
        margin: 0 2px 0 2px;
        border-radius: 4px;
    }}
    QScrollBar::handle:horizontal {{
        background: {p['border']};
        min-width: 28px;
        border-radius: 4px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {p['control_border']};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
        background: transparent;
        width: 0px;
    }}
    QPushButton#TableActionButton {{
        background-color: {p['accent_tint']};
        color: {p['accent_tint_ink']};
        border: 1px solid {p['accent']};
        border-radius: 6px;
        padding: 4px 10px;
        font-weight: 600;
        font-size: 9pt;
    }}
    QPushButton#TableActionButton:hover {{
        background-color: {p['accent']};
        color: {p['accent_ink']};
    }}
    """


class EnvCheckWorker(QtCore.QThread):
    """Non-blocking lightweight check for Waydroid and ADB connectivity."""

    snapshot_ready = QtCore.pyqtSignal(object)

    def __init__(self, repo: Path, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self.repo = repo

    def run(self) -> None:
        snap = gui_core.detect_environment_snapshot(self.repo)
        self.snapshot_ready.emit(snap)


class CheckoutApprovalDialog(QtWidgets.QDialog):
    """Explicit modal approval gate required before any checkout step."""

    def __init__(
        self,
        step: gui_core.GuidedStep,
        parent: QtWidgets.QWidget | None = None,
        lock_no_tap: bool = False,
    ) -> None:
        super().__init__(parent)
        self.step = step
        self.setWindowTitle(f"Konfirmasi Checkout: {step.badge}")
        self.setModal(True)
        self.setMinimumWidth(480)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        heading = QtWidgets.QLabel(f"Konfirmasi sebelum membuka {step.title}")
        heading.setObjectName("SectionTitle")
        heading.setWordWrap(True)
        layout.addWidget(heading)

        warn_box = QtWidgets.QFrame()
        warn_box.setObjectName("NoticeWarn")
        warn_layout = QtWidgets.QVBoxLayout(warn_box)
        warn_layout.setContentsMargins(12, 10, 12, 10)
        warn_text = QtWidgets.QLabel(
            "PERINGATAN TAGIHAN NYATA: Tahap ini dapat membuka checkout Google Play "
            "dan memicu biaya langganan jika akun tidak memenuhi syarat atau setelah "
            "masa uji coba berakhir. Metadata fase awal 0 bukan jaminan aktivasi gratis."
        )
        warn_text.setWordWrap(True)
        warn_layout.addWidget(warn_text)
        layout.addWidget(warn_box)

        meta = QtWidgets.QLabel(
            f"Product ID: {step.product_id or '-'}\n"
            f"Offer ID:   {step.offer_id or '-'}\n"
            "Keamanan:   Akun Google Play diverifikasi tanpa --force."
        )
        meta.setObjectName("MonoMeta")
        layout.addWidget(meta)

        self.no_tap_checkbox = QtWidgets.QCheckBox(
            "Mode Tinjau Manual (--no-tap): buka sheet Google Play tanpa klik Subscribe otomatis"
        )
        self.no_tap_checkbox.setChecked(True if lock_no_tap else step.default_no_tap)
        if lock_no_tap:
            self.no_tap_checkbox.setEnabled(False)
        else:
            self.no_tap_checkbox.setCursor(QtCore.Qt.PointingHandCursor)
        layout.addWidget(self.no_tap_checkbox)

        self.active_checkbox: QtWidgets.QCheckBox | None = None
        if step.requires_active_plan:
            self.active_checkbox = QtWidgets.QCheckBox(
                "Saya sudah memeriksa langganan aktif dan tanggal perpanjangan sebelumnya di Google Play"
            )
            self.active_checkbox.setChecked(False)
            self.active_checkbox.setCursor(QtCore.Qt.PointingHandCursor)
            self.active_checkbox.stateChanged.connect(self._sync_proceed_state)
            layout.addWidget(self.active_checkbox)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch(1)

        cancel_btn = QtWidgets.QPushButton("Batal")
        cancel_btn.setObjectName("SecondaryButton")
        cancel_btn.setCursor(QtCore.Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        self.proceed_btn = QtWidgets.QPushButton("Setuju && Lanjutkan")
        self.proceed_btn.setObjectName("PrimaryButton")
        self.proceed_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.proceed_btn.clicked.connect(self.accept)
        btn_row.addWidget(self.proceed_btn)
        layout.addLayout(btn_row)

        self._sync_proceed_state()

    def _sync_proceed_state(self) -> None:
        allowed = True
        if self.active_checkbox is not None:
            allowed = self.active_checkbox.isChecked()
        self.proceed_btn.setEnabled(allowed)

    @property
    def use_no_tap(self) -> bool:
        return self.no_tap_checkbox.isChecked()

    @property
    def active_plan_confirmed(self) -> bool:
        return bool(self.active_checkbox and self.active_checkbox.isChecked())


class DesktopToolkitWindow(QtWidgets.QMainWindow):
    """Main window for ePlus AI Toolkit Desktop GUI."""

    def __init__(self, repo: Path = ROOT, auto_probe: bool = True) -> None:
        super().__init__()
        self.repo = repo
        self.settings = QtCore.QSettings("ePlusAIToolkit", "DesktopGUI")
        saved_theme = str(self.settings.value("theme", "dark"))
        self.theme = saved_theme if saved_theme in ("light", "dark") else "dark"

        self.selected_step_key = "step0"
        self.step_statuses: dict[str, str] = {step.key: "Siap" for step in gui_core.GUIDED_STEPS}
        self.env_snapshot = gui_core.EnvironmentSnapshot(
            waydroid_state="Memeriksa...",
            waydroid_ip="",
            adb_serial="",
            adb_available=False,
            venv_ready=(repo / ".venv" / "bin" / "python").is_file(),
        )
        self.detected_offers: list[gui_core.OfferRow] = []
        self.queried_sku_count = 0
        self.detected_account = ""

        self.active_process: QtCore.QProcess | None = None
        self.active_job_kind: str = ""  # "step" | "sku"
        self.active_step_key: str = ""
        self.active_is_checkout: bool = False
        self.job_started_at: float = 0.0
        self.job_raw_output: list[str] = []
        self.stop_requested: bool = False
        self.env_worker: EnvCheckWorker | None = None

        self.setWindowTitle("ePlus AI Toolkit")
        self.resize(1160, 780)
        self.setMinimumSize(860, 580)
        if ICON_PATH.is_file():
            self.setWindowIcon(QtGui.QIcon(str(ICON_PATH)))

        self.elapsed_timer = QtCore.QTimer(self)
        self.elapsed_timer.setInterval(500)
        self.elapsed_timer.timeout.connect(self._tick_elapsed)

        self._build_ui()
        self._apply_theme(self.theme)
        self._select_step("step0")
        self._switch_page(0)
        self._sync_busy_ui()

        if auto_probe:
            self.refresh_environment()

    # ---------- UI Construction ----------
    def _build_ui(self) -> None:
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root_layout = QtWidgets.QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_nav_rail())

        self.pages = QtWidgets.QStackedWidget()
        self.pages.addWidget(self._build_guide_page())
        self.pages.addWidget(self._build_offer_page())
        self.pages.addWidget(self._build_log_page())
        root_layout.addWidget(self.pages, 1)

        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+1"), self, activated=lambda: self._switch_page(0))
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+2"), self, activated=lambda: self._switch_page(1))
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+3"), self, activated=lambda: self._switch_page(2))

    def _build_nav_rail(self) -> QtWidgets.QFrame:
        rail = QtWidgets.QFrame()
        rail.setObjectName("NavRail")
        rail.setFixedWidth(248)
        layout = QtWidgets.QVBoxLayout(rail)
        layout.setContentsMargins(14, 18, 14, 16)
        layout.setSpacing(10)

        brand_row = QtWidgets.QHBoxLayout()
        brand_row.setSpacing(10)
        icon_label = QtWidgets.QLabel()
        if ICON_PATH.is_file():
            pix = QtGui.QIcon(str(ICON_PATH)).pixmap(34, 34)
            icon_label.setPixmap(pix)
        icon_label.setFixedSize(34, 34)
        brand_row.addWidget(icon_label)

        brand_text = QtWidgets.QVBoxLayout()
        brand_text.setSpacing(1)
        title = QtWidgets.QLabel("ePlus AI Toolkit")
        title.setObjectName("AppTitle")
        sub = QtWidgets.QLabel("Waydroid Desktop")
        sub.setObjectName("Muted")
        brand_text.addWidget(title)
        brand_text.addWidget(sub)
        brand_row.addLayout(brand_text, 1)
        layout.addLayout(brand_row)

        nav_label = QtWidgets.QLabel("NAVIGASI")
        nav_label.setObjectName("Muted")
        nav_label.setContentsMargins(4, 10, 0, 2)
        layout.addWidget(nav_label)

        self.nav_buttons: list[QtWidgets.QPushButton] = []
        nav_items = (
            ("1. Panduan Langkah", 0),
            ("2. Deteksi Offer", 1),
            ("3. Log && Diagnostik", 2),
        )
        for label, idx in nav_items:
            btn = QtWidgets.QPushButton(label)
            btn.setObjectName("NavButton")
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.clicked.connect(lambda _checked=False, page=idx: self._switch_page(page))
            layout.addWidget(btn)
            self.nav_buttons.append(btn)

        layout.addStretch(1)

        env_card = QtWidgets.QFrame()
        env_card.setObjectName("EnvCard")
        env_layout = QtWidgets.QVBoxLayout(env_card)
        env_layout.setContentsMargins(12, 12, 12, 12)
        env_layout.setSpacing(6)

        env_title = QtWidgets.QLabel("Status Waydroid")
        env_title.setObjectName("SectionTitle")
        env_layout.addWidget(env_title)

        self.env_waydroid_label = QtWidgets.QLabel("Waydroid: Memeriksa...")
        self.env_waydroid_label.setObjectName("Muted")
        self.env_waydroid_label.setWordWrap(True)
        env_layout.addWidget(self.env_waydroid_label)

        self.env_adb_label = QtWidgets.QLabel("ADB: Memeriksa...")
        self.env_adb_label.setObjectName("Muted")
        self.env_adb_label.setWordWrap(True)
        env_layout.addWidget(self.env_adb_label)

        self.env_account_label = QtWidgets.QLabel("Akun: Belum dicek")
        self.env_account_label.setObjectName("Muted")
        self.env_account_label.setWordWrap(True)
        env_layout.addWidget(self.env_account_label)

        env_btn_row = QtWidgets.QHBoxLayout()
        env_btn_row.setSpacing(6)
        self.refresh_env_btn = QtWidgets.QPushButton("Refresh")
        self.refresh_env_btn.setObjectName("SecondaryButton")
        self.refresh_env_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.refresh_env_btn.clicked.connect(self.refresh_environment)
        env_btn_row.addWidget(self.refresh_env_btn)

        self.open_waydroid_btn = QtWidgets.QPushButton("Buka UI")
        self.open_waydroid_btn.setObjectName("SecondaryButton")
        self.open_waydroid_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.open_waydroid_btn.clicked.connect(self.launch_waydroid_ui)
        env_btn_row.addWidget(self.open_waydroid_btn)
        env_layout.addLayout(env_btn_row)
        layout.addWidget(env_card)

        self.theme_btn = QtWidgets.QPushButton("Ganti ke Tema Terang")
        self.theme_btn.setObjectName("SecondaryButton")
        self.theme_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.theme_btn.clicked.connect(self.toggle_theme)
        layout.addWidget(self.theme_btn)

        return rail

    def _build_guide_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        header = QtWidgets.QHBoxLayout()
        title_box = QtWidgets.QVBoxLayout()
        title_box.setSpacing(2)
        title = QtWidgets.QLabel("Panduan Step-by-Step")
        title.setObjectName("PageTitle")
        subtitle = QtWidgets.QLabel(
            "Ikuti langkah dari atas ke bawah. Mulai dari cek lingkungan dan deteksi offer sebelum membuka checkout."
        )
        subtitle.setObjectName("Muted")
        subtitle.setWordWrap(True)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box, 1)

        self.quick_detect_btn = QtWidgets.QPushButton("Cek Cepat: Deteksi Offer")
        self.quick_detect_btn.setObjectName("SecondaryButton")
        self.quick_detect_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.quick_detect_btn.clicked.connect(self._jump_and_scan_pro)
        header.addWidget(self.quick_detect_btn)
        layout.addLayout(header)

        status_strip = QtWidgets.QFrame()
        status_strip.setObjectName("StatusStrip")
        strip_layout = QtWidgets.QHBoxLayout(status_strip)
        strip_layout.setContentsMargins(14, 10, 14, 10)
        strip_layout.setSpacing(12)

        self.live_badge = QtWidgets.QLabel("SIAP")
        self.live_badge.setObjectName("BadgeNeutral")
        strip_layout.addWidget(self.live_badge)

        self.live_status_text = QtWidgets.QLabel(
            "Belum ada proses berjalan. Pilih Step 0 untuk cek Waydroid atau klik Cek Cepat: Deteksi Offer."
        )
        self.live_status_text.setWordWrap(True)
        strip_layout.addWidget(self.live_status_text, 1)

        self.guide_stop_btn = QtWidgets.QPushButton("Hentikan")
        self.guide_stop_btn.setObjectName("DangerButton")
        self.guide_stop_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.guide_stop_btn.clicked.connect(self.stop_readonly_job)
        self.guide_stop_btn.setVisible(False)
        strip_layout.addWidget(self.guide_stop_btn)
        layout.addWidget(status_strip)

        body = QtWidgets.QHBoxLayout()
        body.setSpacing(16)

        step_scroll = QtWidgets.QScrollArea()
        step_scroll.setWidgetResizable(True)
        step_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        step_scroll.setFixedWidth(308)
        step_container = QtWidgets.QWidget()
        step_list_layout = QtWidgets.QVBoxLayout(step_container)
        step_list_layout.setContentsMargins(0, 0, 8, 0)
        step_list_layout.setSpacing(8)

        self.step_buttons: dict[str, QtWidgets.QPushButton] = {}
        for step in gui_core.GUIDED_STEPS:
            btn = QtWidgets.QPushButton()
            btn.setObjectName("StepItem")
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.clicked.connect(lambda _checked=False, k=step.key: self._select_step(k))
            step_list_layout.addWidget(btn)
            self.step_buttons[step.key] = btn
        step_list_layout.addStretch(1)
        step_scroll.setWidget(step_container)
        body.addWidget(step_scroll)

        detail_card = QtWidgets.QFrame()
        detail_card.setObjectName("DetailCard")
        detail_outer = QtWidgets.QVBoxLayout(detail_card)
        detail_outer.setContentsMargins(20, 18, 20, 18)
        detail_outer.setSpacing(12)

        detail_scroll = QtWidgets.QScrollArea()
        detail_scroll.setWidgetResizable(True)
        detail_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        detail_inner_widget = QtWidgets.QWidget()
        detail_layout = QtWidgets.QVBoxLayout(detail_inner_widget)
        detail_layout.setContentsMargins(0, 0, 6, 0)
        detail_layout.setSpacing(11)

        top_meta = QtWidgets.QHBoxLayout()
        self.detail_badge = QtWidgets.QLabel("Step 0")
        self.detail_badge.setObjectName("BadgeNeutral")
        self.detail_risk_badge = QtWidgets.QLabel("Read-Only")
        self.detail_risk_badge.setObjectName("BadgeOk")
        top_meta.addWidget(self.detail_badge)
        top_meta.addWidget(self.detail_risk_badge)
        top_meta.addStretch(1)
        detail_layout.addLayout(top_meta)

        self.detail_title = QtWidgets.QLabel()
        self.detail_title.setObjectName("PageTitle")
        self.detail_title.setWordWrap(True)
        detail_layout.addWidget(self.detail_title)

        self.detail_summary = QtWidgets.QLabel()
        self.detail_summary.setWordWrap(True)
        detail_layout.addWidget(self.detail_summary)

        self.detail_sku_meta = QtWidgets.QLabel()
        self.detail_sku_meta.setObjectName("MonoMeta")
        self.detail_sku_meta.setWordWrap(True)
        detail_layout.addWidget(self.detail_sku_meta)

        checklist_heading = QtWidgets.QLabel("Yang perlu Anda lakukan:")
        checklist_heading.setObjectName("SectionTitle")
        detail_layout.addWidget(checklist_heading)

        self.detail_checklist = QtWidgets.QLabel()
        self.detail_checklist.setWordWrap(True)
        detail_layout.addWidget(self.detail_checklist)

        self.detail_notice_box = QtWidgets.QFrame()
        self.detail_notice_box.setObjectName("NoticeNeutral")
        notice_inner = QtWidgets.QVBoxLayout(self.detail_notice_box)
        notice_inner.setContentsMargins(12, 9, 12, 9)
        self.detail_notice_text = QtWidgets.QLabel()
        self.detail_notice_text.setWordWrap(True)
        notice_inner.addWidget(self.detail_notice_text)
        detail_layout.addWidget(self.detail_notice_box)

        self.result_box = QtWidgets.QFrame()
        self.result_box.setObjectName("NoticeNeutral")
        result_inner = QtWidgets.QVBoxLayout(self.result_box)
        result_inner.setContentsMargins(12, 9, 12, 9)
        result_inner.setSpacing(4)
        self.result_title = QtWidgets.QLabel()
        self.result_title.setObjectName("SectionTitle")
        self.result_title.setWordWrap(True)
        self.result_body = QtWidgets.QLabel()
        self.result_body.setWordWrap(True)
        result_inner.addWidget(self.result_title)
        result_inner.addWidget(self.result_body)
        self.result_box.setVisible(False)
        detail_layout.addWidget(self.result_box)

        detail_layout.addStretch(1)
        detail_scroll.setWidget(detail_inner_widget)
        detail_outer.addWidget(detail_scroll, 1)

        action_row = QtWidgets.QHBoxLayout()
        action_row.setSpacing(10)
        self.run_step_btn = QtWidgets.QPushButton()
        self.run_step_btn.setObjectName("PrimaryButton")
        self.run_step_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.run_step_btn.clicked.connect(self._trigger_selected_step)
        action_row.addWidget(self.run_step_btn)

        self.view_log_btn = QtWidgets.QPushButton("Buka Log")
        self.view_log_btn.setObjectName("SecondaryButton")
        self.view_log_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.view_log_btn.clicked.connect(lambda: self._switch_page(2))
        action_row.addWidget(self.view_log_btn)
        action_row.addStretch(1)
        detail_outer.addLayout(action_row)

        body.addWidget(detail_card, 1)

        layout.addLayout(body, 1)
        self._refresh_step_buttons()
        return page

    def _build_offer_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QtWidgets.QLabel("Deteksi Offer Google Play (Read-Only)")
        title.setObjectName("PageTitle")
        subtitle = QtWidgets.QLabel(
            "Memindai SKU dan fase awal 0 langsung dari BillingClient di Waydroid tanpa membuka checkout."
        )
        subtitle.setObjectName("Muted")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        controls_card = QtWidgets.QFrame()
        controls_card.setObjectName("Card")
        ctrl_layout = QtWidgets.QVBoxLayout(controls_card)
        ctrl_layout.setContentsMargins(14, 14, 14, 14)
        ctrl_layout.setSpacing(10)

        row1 = QtWidgets.QHBoxLayout()
        row1.setSpacing(10)

        preset_lbl = QtWidgets.QLabel("Kategori SKU:")
        row1.addWidget(preset_lbl)
        self.preset_combo = QtWidgets.QComboBox()
        self.preset_combo.setCursor(QtCore.Qt.PointingHandCursor)
        for key, label in gui_core.SKU_PRESET_CHOICES:
            self.preset_combo.addItem(label, key)
        row1.addWidget(self.preset_combo, 1)

        self.only_free_check = QtWidgets.QCheckBox("Hanya fase awal gratis (0)")
        self.only_free_check.setCursor(QtCore.Qt.PointingHandCursor)
        self.only_free_check.stateChanged.connect(self._render_offer_table)
        row1.addWidget(self.only_free_check)

        self.scan_btn = QtWidgets.QPushButton("Deteksi Offer Sekarang")
        self.scan_btn.setObjectName("PrimaryButton")
        self.scan_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.scan_btn.clicked.connect(self.start_offer_scan)
        row1.addWidget(self.scan_btn)

        self.scan_stop_btn = QtWidgets.QPushButton("Hentikan")
        self.scan_stop_btn.setObjectName("DangerButton")
        self.scan_stop_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.scan_stop_btn.clicked.connect(self.stop_readonly_job)
        self.scan_stop_btn.setVisible(False)
        row1.addWidget(self.scan_stop_btn)
        ctrl_layout.addLayout(row1)

        row2 = QtWidgets.QHBoxLayout()
        row2.setSpacing(10)
        search_lbl = QtWidgets.QLabel("Filter:")
        row2.addWidget(search_lbl)
        self.offer_search = QtWidgets.QLineEdit()
        self.offer_search.setPlaceholderText("Cari SKU, offer ID, atau durasi (contoh: 18months, ultra, 12 bulan)")
        self.offer_search.textChanged.connect(self._render_offer_table)
        row2.addWidget(self.offer_search, 1)

        self.offer_summary_label = QtWidgets.QLabel("Belum dipindai")
        self.offer_summary_label.setObjectName("Muted")
        row2.addWidget(self.offer_summary_label)
        ctrl_layout.addLayout(row2)
        layout.addWidget(controls_card)

        self.offer_states = QtWidgets.QStackedWidget()

        # State 0: Empty
        empty_card = QtWidgets.QFrame()
        empty_card.setObjectName("Card")
        empty_layout = QtWidgets.QVBoxLayout(empty_card)
        empty_layout.setContentsMargins(28, 36, 28, 36)
        empty_layout.setSpacing(10)
        empty_layout.setAlignment(QtCore.Qt.AlignCenter)
        empty_title = QtWidgets.QLabel("Belum ada hasil pemindaian offer")
        empty_title.setObjectName("SectionTitle")
        empty_title.setAlignment(QtCore.Qt.AlignCenter)
        empty_desc = QtWidgets.QLabel(
            "Pilih kategori SKU (disarankan Google AI Pro 5 TB untuk cek cepat 18 bulan / 15 bulan / 12 bulan), "
            "lalu tekan Deteksi Offer Sekarang. Mode ini 100% read-only."
        )
        empty_desc.setObjectName("Muted")
        empty_desc.setWordWrap(True)
        empty_desc.setAlignment(QtCore.Qt.AlignCenter)
        self.empty_scan_btn = QtWidgets.QPushButton("Mulai Deteksi Offer Pro 5 TB")
        self.empty_scan_btn.setObjectName("PrimaryButton")
        self.empty_scan_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.empty_scan_btn.clicked.connect(self._jump_and_scan_pro)
        empty_layout.addWidget(empty_title)
        empty_layout.addWidget(empty_desc)
        empty_layout.addWidget(self.empty_scan_btn, 0, QtCore.Qt.AlignCenter)
        self.offer_states.addWidget(empty_card)

        # State 1: Loading
        loading_card = QtWidgets.QFrame()
        loading_card.setObjectName("Card")
        loading_layout = QtWidgets.QVBoxLayout(loading_card)
        loading_layout.setContentsMargins(28, 36, 28, 36)
        loading_layout.setSpacing(10)
        loading_layout.setAlignment(QtCore.Qt.AlignCenter)
        self.loading_title = QtWidgets.QLabel("Memindai offer dari Google Play BillingClient...")
        self.loading_title.setObjectName("SectionTitle")
        self.loading_title.setAlignment(QtCore.Qt.AlignCenter)
        self.loading_detail = QtWidgets.QLabel("Menghubungkan ke Waydroid dan melampirkan Frida (read-only)...")
        self.loading_detail.setObjectName("Muted")
        self.loading_detail.setWordWrap(True)
        self.loading_detail.setAlignment(QtCore.Qt.AlignCenter)
        loading_layout.addWidget(self.loading_title)
        loading_layout.addWidget(self.loading_detail)
        self.offer_states.addWidget(loading_card)

        # State 2: Error
        error_card = QtWidgets.QFrame()
        error_card.setObjectName("NoticeDanger")
        error_layout = QtWidgets.QVBoxLayout(error_card)
        error_layout.setContentsMargins(24, 24, 24, 24)
        error_layout.setSpacing(10)
        self.offer_error_title = QtWidgets.QLabel("Pemindaian offer gagal")
        self.offer_error_title.setObjectName("SectionTitle")
        self.offer_error_detail = QtWidgets.QLabel(
            "Pastikan Waydroid aktif, Google Play Store sudah login, dan jalankan Step 0 untuk diagnostik."
        )
        self.offer_error_detail.setWordWrap(True)
        err_btns = QtWidgets.QHBoxLayout()
        retry_btn = QtWidgets.QPushButton("Coba Pindai Lagi")
        retry_btn.setObjectName("PrimaryButton")
        retry_btn.setCursor(QtCore.Qt.PointingHandCursor)
        retry_btn.clicked.connect(self.start_offer_scan)
        open_log_btn = QtWidgets.QPushButton("Buka Log && Diagnostik")
        open_log_btn.setObjectName("SecondaryButton")
        open_log_btn.setCursor(QtCore.Qt.PointingHandCursor)
        open_log_btn.clicked.connect(lambda: self._switch_page(2))
        err_btns.addWidget(retry_btn)
        err_btns.addWidget(open_log_btn)
        err_btns.addStretch(1)
        error_layout.addWidget(self.offer_error_title)
        error_layout.addWidget(self.offer_error_detail)
        error_layout.addLayout(err_btns)
        error_layout.addStretch(1)
        self.offer_states.addWidget(error_card)

        # State 3: Results table
        table_container = QtWidgets.QWidget()
        table_layout = QtWidgets.QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(8)

        self.offer_table = QtWidgets.QTableWidget(0, 6)
        self.offer_table.setHorizontalHeaderLabels(
            ["Produk", "Durasi", "Fase Awal", "SKU ID", "Offer ID", "Aksi"]
        )
        self.offer_table.setAlternatingRowColors(False)
        self.offer_table.setWordWrap(False)
        self.offer_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.offer_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.offer_table.verticalHeader().setVisible(False)
        header_view = self.offer_table.horizontalHeader()
        header_view.setStretchLastSection(False)
        header_view.setSectionResizeMode(0, QtWidgets.QHeaderView.Interactive)
        header_view.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
        header_view.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(5, QtWidgets.QHeaderView.Fixed)
        self.offer_table.setColumnWidth(0, 195)
        self.offer_table.setColumnWidth(5, 136)
        table_layout.addWidget(self.offer_table, 1)

        disclaimer = QtWidgets.QLabel(
            "Catatan: Metadata BillingClient bersifat read-only dan tidak menjamin kelayakan akun "
            "di sisi server atau persetujuan checkout gratis di Google Play."
        )
        disclaimer.setObjectName("Muted")
        disclaimer.setWordWrap(True)
        table_layout.addWidget(disclaimer)
        self.offer_states.addWidget(table_container)

        self.offer_states.setCurrentIndex(0)
        layout.addWidget(self.offer_states, 1)
        return page

    def _build_log_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        header = QtWidgets.QHBoxLayout()
        title_box = QtWidgets.QVBoxLayout()
        title_box.setSpacing(2)
        title = QtWidgets.QLabel("Log & Diagnostik")
        title.setObjectName("PageTitle")
        subtitle = QtWidgets.QLabel(
            "Output langsung dari engine. Alamat email otomatis disamarkan dan token pembayaran tidak pernah dicetak."
        )
        subtitle.setObjectName("Muted")
        subtitle.setWordWrap(True)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box, 1)

        self.copy_log_btn = QtWidgets.QPushButton("Salin Log Aman")
        self.copy_log_btn.setObjectName("SecondaryButton")
        self.copy_log_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.copy_log_btn.clicked.connect(self._copy_logs)
        header.addWidget(self.copy_log_btn)

        self.clear_log_btn = QtWidgets.QPushButton("Bersihkan")
        self.clear_log_btn.setObjectName("SecondaryButton")
        self.clear_log_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.clear_log_btn.clicked.connect(self._clear_logs)
        header.addWidget(self.clear_log_btn)
        layout.addLayout(header)

        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setObjectName("LogView")
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("Log eksekusi akan muncul di sini saat Anda menjalankan Step atau Deteksi Offer.")
        layout.addWidget(self.log_view, 1)

        footer = QtWidgets.QHBoxLayout()
        footer.setSpacing(12)
        credit_lbl = QtWidgets.QLabel("Kredit & Sumber:")
        credit_lbl.setObjectName("Muted")
        footer.addWidget(credit_lbl)

        upstream_btn = QtWidgets.QPushButton("Upstream: gylive/google-ultra")
        upstream_btn.setObjectName("SecondaryButton")
        upstream_btn.setCursor(QtCore.Qt.PointingHandCursor)
        upstream_btn.clicked.connect(
            lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl("https://github.com/gylive/google-ultra"))
        )
        footer.addWidget(upstream_btn)

        maint_btn = QtWidgets.QPushButton("Maintainer: @hoangsvit")
        maint_btn.setObjectName("SecondaryButton")
        maint_btn.setCursor(QtCore.Qt.PointingHandCursor)
        maint_btn.clicked.connect(
            lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl("https://github.com/hoangsvit"))
        )
        footer.addWidget(maint_btn)
        footer.addStretch(1)
        layout.addLayout(footer)
        return page

    # ---------- Theme & Navigation ----------
    def _apply_theme(self, theme: str) -> None:
        self.theme = theme
        qss = build_stylesheet(theme)
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.setStyleSheet(qss)
        else:
            self.setStyleSheet(qss)
        self.theme_btn.setText("Ganti ke Tema Terang" if theme == "dark" else "Ganti ke Tema Gelap")
        self.settings.setValue("theme", theme)
        for widget in self.findChildren(QtWidgets.QWidget):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()

    def toggle_theme(self) -> None:
        self._apply_theme("light" if self.theme == "dark" else "dark")

    def _switch_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        for idx, btn in enumerate(self.nav_buttons):
            btn.setProperty("active", "true" if idx == index else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _refresh_step_buttons(self) -> None:
        for step in gui_core.GUIDED_STEPS:
            btn = self.step_buttons[step.key]
            status = self.step_statuses.get(step.key, "Siap")
            kind = "Checkout" if step.is_checkout else "Read-Only"
            short_title = step.title.replace("Checkout ", "").replace("&", "&&")
            btn.setText(f"{step.badge}  |  {status}  ({kind})\n{short_title}")
            btn.setProperty("selected", "true" if step.key == self.selected_step_key else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _select_step(self, step_key: str) -> None:
        if step_key not in gui_core.STEP_BY_KEY:
            return
        self.selected_step_key = step_key
        step = gui_core.STEP_BY_KEY[step_key]
        self.detail_badge.setText(step.badge)
        self.detail_risk_badge.setText("Checkout (Tagihan Nyata)" if step.is_checkout else "Read-Only / Diagnostik")
        self.detail_risk_badge.setObjectName("BadgeWarn" if step.is_checkout else "BadgeOk")
        self.detail_risk_badge.style().unpolish(self.detail_risk_badge)
        self.detail_risk_badge.style().polish(self.detail_risk_badge)

        self.detail_title.setText(step.title)
        self.detail_summary.setText(step.summary)

        if step.product_id or step.offer_id:
            self.detail_sku_meta.setText(
                f"Product ID: {step.product_id or '-'}   |   Offer ID: {step.offer_id or 'Semua offer aktif'}"
            )
            self.detail_sku_meta.setVisible(True)
        else:
            self.detail_sku_meta.setVisible(False)

        checklist_lines = "\n".join(f"{idx}. {item}" for idx, item in enumerate(step.checklist, 1))
        self.detail_checklist.setText(checklist_lines)

        self.detail_notice_text.setText(step.safety_note)
        self.detail_notice_box.setObjectName("NoticeWarn" if step.is_checkout else "NoticeNeutral")
        self.detail_notice_box.style().unpolish(self.detail_notice_box)
        self.detail_notice_box.style().polish(self.detail_notice_box)

        self.run_step_btn.setText(step.cta_label.replace("&", "&&"))
        self._refresh_step_buttons()
        self._sync_busy_ui()

    # ---------- Environment Status ----------
    def refresh_environment(self) -> None:
        if self.env_worker is not None and self.env_worker.isRunning():
            return
        self.env_waydroid_label.setText("Waydroid: Memeriksa...")
        self.env_worker = EnvCheckWorker(self.repo, self)
        self.env_worker.snapshot_ready.connect(self._on_env_snapshot)
        self.env_worker.start()

    def _on_env_snapshot(self, snap: gui_core.EnvironmentSnapshot) -> None:
        self.env_snapshot = snap
        wd = snap.waydroid_state
        if snap.waydroid_ip:
            wd = f"{wd} ({snap.waydroid_ip})"
        self.env_waydroid_label.setText(f"Waydroid: {wd}")
        if snap.adb_serial:
            self.env_adb_label.setText(f"ADB: Terhubung ({snap.adb_serial})")
        elif snap.adb_available:
            self.env_adb_label.setText("ADB: Belum ada perangkat online")
        else:
            self.env_adb_label.setText("ADB: Tidak ditemukan")
        if self.detected_account:
            self.env_account_label.setText(f"Akun: {gui_core.sanitize_log_line(self.detected_account)}")

    def launch_waydroid_ui(self) -> None:
        if not shutil.which("waydroid"):
            QtWidgets.QMessageBox.warning(
                self,
                "Waydroid Tidak Ditemukan",
                "Perintah 'waydroid' tidak tersedia di sistem ini.",
            )
            return
        try:
            subprocess.Popen(
                ["waydroid", "show-full-ui"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            self._append_log("Membuka jendela Waydroid UI...")
            QtCore.QTimer.singleShot(2500, self.refresh_environment)
        except OSError as exc:
            QtWidgets.QMessageBox.warning(self, "Gagal Membuka Waydroid", str(exc))

    # ---------- Busy State & Process Orchestration ----------
    def is_busy(self) -> bool:
        return self.active_process is not None and self.active_process.state() != QtCore.QProcess.NotRunning

    def _sync_busy_ui(self) -> None:
        busy = self.is_busy()
        can_stop = busy and not self.active_is_checkout

        self.run_step_btn.setEnabled(not busy)
        self.quick_detect_btn.setEnabled(not busy)
        self.scan_btn.setEnabled(not busy)
        self.empty_scan_btn.setEnabled(not busy)
        self.preset_combo.setEnabled(not busy)
        for btn in self.step_buttons.values():
            btn.setEnabled(not busy)
        if hasattr(self, "offer_table"):
            for r in range(self.offer_table.rowCount()):
                holder = self.offer_table.cellWidget(r, 5)
                if holder is not None:
                    for child_btn in holder.findChildren(QtWidgets.QPushButton):
                        child_btn.setEnabled(not busy)

        self.guide_stop_btn.setVisible(busy)
        self.guide_stop_btn.setEnabled(can_stop)
        self.guide_stop_btn.setText("Hentikan" if can_stop else "Checkout Berjalan (Jangan Tutup)")

        self.scan_stop_btn.setVisible(busy and self.active_job_kind == "sku")
        self.scan_stop_btn.setEnabled(can_stop)

    def _tick_elapsed(self) -> None:
        if not self.is_busy():
            self.elapsed_timer.stop()
            return
        secs = int(time.monotonic() - self.job_started_at)
        if self.active_job_kind == "sku":
            self.live_status_text.setText(f"Sedang memindai offer (read-only)... {secs} detik")
            self.loading_title.setText(f"Memindai offer Google Play... ({secs} detik)")
        else:
            step = gui_core.STEP_BY_KEY.get(self.active_step_key)
            label = step.title if step else self.active_step_key
            self.live_status_text.setText(f"Menjalankan {label}... {secs} detik")

    def _append_log(self, raw_text: str) -> None:
        for line in raw_text.splitlines():
            clean = gui_core.sanitize_log_line(line)
            self.log_view.appendPlainText(clean)

    def _copy_logs(self) -> None:
        QtWidgets.QApplication.clipboard().setText(self.log_view.toPlainText())
        self.copy_log_btn.setText("Log Disalin")
        QtCore.QTimer.singleShot(1800, lambda: self.copy_log_btn.setText("Salin Log Aman"))

    def _clear_logs(self) -> None:
        self.log_view.clear()

    def _launch_subprocess(self, command: list[str], kind: str, step_key: str, is_checkout: bool) -> None:
        if self.is_busy():
            return
        self.active_job_kind = kind
        self.active_step_key = step_key
        self.active_is_checkout = is_checkout
        self.job_started_at = time.monotonic()
        self.job_wall_start = time.time()
        self.job_raw_output = []
        self.stop_requested = False

        proc = QtCore.QProcess(self)
        proc.setWorkingDirectory(str(self.repo))
        env = QtCore.QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONIOENCODING", "utf-8:backslashreplace")
        env.insert("PYTHONUTF8", "1")
        env.insert("PYTHONUNBUFFERED", "1")
        proc.setProcessEnvironment(env)
        proc.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        proc.readyReadStandardOutput.connect(self._on_process_output)
        proc.finished.connect(self._on_process_finished)
        proc.errorOccurred.connect(self._on_process_error)

        self.active_process = proc
        self.live_badge.setText("BERJALAN")
        self.live_badge.setObjectName("BadgeWarn" if is_checkout else "BadgeOk")
        self.live_badge.style().unpolish(self.live_badge)
        self.live_badge.style().polish(self.live_badge)

        if kind == "step" and step_key in self.step_statuses:
            self.step_statuses[step_key] = "Berjalan"
            self._refresh_step_buttons()
            self.result_box.setVisible(False)
        elif kind == "sku":
            self.offer_states.setCurrentIndex(1)
            self.loading_detail.setText("Menghubungkan ke Waydroid dan menyiapkan sesi BillingClient read-only...")

        self._append_log(f"--- Memulai proses ({kind}: {step_key or 'sku-scan'}) ---")
        self._sync_busy_ui()
        self.elapsed_timer.start()
        proc.start(command[0], command[1:])

    def _on_process_output(self) -> None:
        if self.active_process is None:
            return
        chunk = bytes(self.active_process.readAllStandardOutput()).decode("utf-8", errors="replace")
        if not chunk:
            return
        self.job_raw_output.append(chunk)
        for line in chunk.splitlines():
            match = ACCOUNT_LINE_RE.match(line.strip())
            if match:
                self.detected_account = match.group(1).strip().lower()
                self.env_account_label.setText(f"Akun: {gui_core.sanitize_log_line(self.detected_account)}")
            if line.startswith("SKU_JSON_RESULT:"):
                continue
            if self.active_job_kind == "sku" and "Querying SKU batch" in line:
                self.loading_detail.setText(line.strip())
            self._append_log(line)

    def _on_process_error(self, error: QtCore.QProcess.ProcessError) -> None:
        if self.stop_requested:
            return
        self._append_log(f"Kesalahan proses subprocess (kode Qt: {int(error)}).")

    def _on_process_finished(self, exit_code: int, _exit_status: QtCore.QProcess.ExitStatus) -> None:
        self.elapsed_timer.stop()
        full_output = "".join(self.job_raw_output)
        kind = self.active_job_kind
        step_key = self.active_step_key
        was_stopped = self.stop_requested

        self.active_process = None
        self.active_job_kind = ""
        self.active_step_key = ""
        self.active_is_checkout = False
        self._sync_busy_ui()

        if was_stopped:
            self.live_badge.setText("DIHENTIKAN")
            self.live_badge.setObjectName("BadgeNeutral")
            self.live_badge.style().unpolish(self.live_badge)
            self.live_badge.style().polish(self.live_badge)
            self.live_status_text.setText("Proses read-only dihentikan oleh pengguna.")
            if kind == "step" and step_key in self.step_statuses:
                self.step_statuses[step_key] = "Dihentikan"
                self._refresh_step_buttons()
            elif kind == "sku":
                self.offer_states.setCurrentIndex(3 if self.detected_offers else 0)
            return

        if kind == "sku":
            self._handle_sku_finished(exit_code, full_output)
        elif kind == "custom_offer":
            self._handle_custom_offer_finished(step_key, exit_code)
        else:
            self._handle_step_finished(step_key, exit_code)

        self.refresh_environment()

    def stop_readonly_job(self) -> None:
        """Stop only read-only jobs; never force-kill an active checkout step."""
        if not self.is_busy() or self.active_is_checkout or self.active_process is None:
            return
        self.stop_requested = True
        self._append_log("Meminta penghentian proses read-only...")
        self.active_process.terminate()
        QtCore.QTimer.singleShot(2500, self._kill_if_still_stopping)

    def _kill_if_still_stopping(self) -> None:
        if self.stop_requested and self.active_process is not None and not self.active_is_checkout:
            if self.active_process.state() != QtCore.QProcess.NotRunning:
                self.active_process.kill()

    # ---------- Guided Step Execution ----------
    def _trigger_selected_step(self) -> None:
        if self.is_busy():
            return
        step = gui_core.STEP_BY_KEY[self.selected_step_key]
        confirmed = False
        active_confirmed = False
        no_tap = step.default_no_tap

        if step.is_checkout:
            dialog = CheckoutApprovalDialog(step, self)
            if dialog.exec_() != QtWidgets.QDialog.Accepted:
                self._append_log(f"Konfirmasi dibatalkan untuk {step.badge}. Tidak ada checkout dimulai.")
                return
            confirmed = True
            active_confirmed = dialog.active_plan_confirmed
            no_tap = dialog.use_no_tap

        try:
            cmd = gui_core.build_step_command(
                step.key,
                self.repo,
                confirmed=confirmed,
                active_confirmed=active_confirmed,
                no_tap=no_tap,
            )
        except (OSError, ValueError) as exc:
            QtWidgets.QMessageBox.warning(self, "Tidak Dapat Menjalankan Tahap", str(exc))
            return

        self._launch_subprocess(cmd, kind="step", step_key=step.key, is_checkout=step.is_checkout)

    def _handle_step_finished(self, step_key: str, exit_code: int) -> None:
        level, title, guidance = gui_core.summarize_step_result(
            step_key, exit_code, self.job_wall_start, self.repo, detected_account=self.detected_account
        )
        if level == "ok":
            self.step_statuses[step_key] = "Selesai"
            self.live_badge.setText("SELESAI")
            self.live_badge.setObjectName("BadgeOk")
            self.result_box.setObjectName("NoticeOk")
        elif level == "warn":
            self.step_statuses[step_key] = "Tinjau"
            self.live_badge.setText("TINJAU")
            self.live_badge.setObjectName("BadgeWarn")
            self.result_box.setObjectName("NoticeWarn")
        else:
            self.step_statuses[step_key] = "Gagal"
            self.live_badge.setText("GAGAL")
            self.live_badge.setObjectName("BadgeDanger")
            self.result_box.setObjectName("NoticeDanger")

        for widget in (self.live_badge, self.result_box):
            widget.style().unpolish(widget)
            widget.style().polish(widget)

        self.live_status_text.setText(f"{title}. {guidance}")
        self.result_title.setText(title)
        self.result_body.setText(guidance)
        self.result_box.setVisible(True)
        self._refresh_step_buttons()

    # ---------- Offer Detector ----------
    def _jump_and_scan_pro(self) -> None:
        if self.is_busy():
            return
        self._switch_page(1)
        self.preset_combo.setCurrentIndex(0)  # pro
        self.start_offer_scan()

    def start_offer_scan(self) -> None:
        if self.is_busy():
            return
        preset = str(self.preset_combo.currentData() or "pro")
        try:
            cmd = gui_core.build_sku_scan_command(
                self.repo,
                preset=preset,
                only_free=False,  # fetch all in preset so UI toggle filters instantly without rescanning
                serial=self.env_snapshot.adb_serial,
            )
        except (OSError, ValueError) as exc:
            self.offer_error_title.setText("Tidak dapat memulai pemindaian")
            self.offer_error_detail.setText(str(exc))
            self.offer_states.setCurrentIndex(2)
            return

        self._launch_subprocess(cmd, kind="sku", step_key=f"preset:{preset}", is_checkout=False)

    def _handle_sku_finished(self, exit_code: int, full_output: str) -> None:
        rows, queried, errors = gui_core.parse_sku_json_output(full_output)
        if exit_code != 0 and not rows:
            self.live_badge.setText("GAGAL")
            self.live_badge.setObjectName("BadgeDanger")
            self.live_badge.style().unpolish(self.live_badge)
            self.live_badge.style().polish(self.live_badge)
            self.live_status_text.setText("Deteksi offer gagal. Periksa Waydroid dan tab Log & Diagnostik.")
            self.offer_error_title.setText("Deteksi offer tidak berhasil")
            self.offer_error_detail.setText(
                "Pastikan Waydroid berjalan, Google Play Store aktif, lalu jalankan Step 0 di Panduan Step-by-Step "
                "atau periksa detail di tab Log & Diagnostik."
            )
            self.offer_states.setCurrentIndex(2)
            return

        self.detected_offers = rows
        self.queried_sku_count = queried
        free_count = sum(1 for r in rows if r.is_free_intro)
        self.live_badge.setText("SELESAI")
        self.live_badge.setObjectName("BadgeOk")
        self.live_badge.style().unpolish(self.live_badge)
        self.live_badge.style().polish(self.live_badge)
        self.live_status_text.setText(
            f"Deteksi selesai: {len(rows)} offer dari {queried} SKU ({free_count} fase awal gratis)."
        )
        if errors:
            self._append_log(f"Peringatan diagnostik pemindaian: {len(errors)} event.")
        self._render_offer_table()
        self.offer_states.setCurrentIndex(3)

    def _render_offer_table(self) -> None:
        filtered = gui_core.filter_offers(
            self.detected_offers,
            query=self.offer_search.text(),
            only_free=self.only_free_check.isChecked(),
        )
        total_free = sum(1 for r in self.detected_offers if r.is_free_intro)
        if self.detected_offers:
            self.offer_summary_label.setText(
                f"Menampilkan {len(filtered)} dari {len(self.detected_offers)} offer "
                f"({total_free} fase awal gratis, {self.queried_sku_count} SKU dipindai)"
            )
        else:
            self.offer_summary_label.setText("Belum dipindai")

        self.offer_table.setRowCount(len(filtered))
        for row_idx, offer in enumerate(filtered):
            prod_label = offer.name or offer.title or offer.product
            self.offer_table.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(prod_label))
            self.offer_table.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(offer.period_human))

            price_item = QtWidgets.QTableWidgetItem(offer.price_human)
            if offer.is_free_intro:
                font = price_item.font()
                font.setBold(True)
                price_item.setFont(font)
            self.offer_table.setItem(row_idx, 2, price_item)

            self.offer_table.setItem(row_idx, 3, QtWidgets.QTableWidgetItem(offer.product))
            self.offer_table.setItem(row_idx, 4, QtWidgets.QTableWidgetItem(offer.offer_id))

            if offer.is_stack_step and offer.guided_step_key:
                step = gui_core.STEP_BY_KEY[offer.guided_step_key]
                holder = QtWidgets.QWidget()
                holder_layout = QtWidgets.QHBoxLayout(holder)
                holder_layout.setContentsMargins(6, 4, 6, 4)
                action_btn = QtWidgets.QPushButton(f"Ke {step.badge}")
                action_btn.setObjectName("TableActionButton")
                action_btn.setCursor(QtCore.Qt.PointingHandCursor)
                action_btn.setEnabled(not self.is_busy())
                action_btn.clicked.connect(
                    lambda _checked=False, k=offer.guided_step_key: self._open_step_from_offer(k)
                )
                holder_layout.addWidget(action_btn)
                self.offer_table.setCellWidget(row_idx, 5, holder)
            elif offer.can_open_checkout:
                holder = QtWidgets.QWidget()
                holder_layout = QtWidgets.QHBoxLayout(holder)
                holder_layout.setContentsMargins(6, 4, 6, 4)
                action_btn = QtWidgets.QPushButton("Buka Checkout")
                action_btn.setObjectName("TableActionButton")
                action_btn.setCursor(QtCore.Qt.PointingHandCursor)
                action_btn.setEnabled(not self.is_busy())
                action_btn.clicked.connect(
                    lambda _checked=False, row=offer: self._trigger_custom_offer_checkout(row)
                )
                holder_layout.addWidget(action_btn)
                self.offer_table.setCellWidget(row_idx, 5, holder)
            else:
                self.offer_table.setItem(row_idx, 5, QtWidgets.QTableWidgetItem("Berbayar"))
            self.offer_table.setRowHeight(row_idx, 42)

    def _open_step_from_offer(self, step_key: str) -> None:
        self._select_step(step_key)
        self._switch_page(0)

    def _trigger_custom_offer_checkout(self, offer: gui_core.OfferRow) -> None:
        if self.is_busy() or not offer.can_open_checkout:
            return
        prod_name = offer.name or offer.title or offer.product
        temp_step = gui_core.GuidedStep(
            key=f"custom:{offer.product}:{offer.offer_id}",
            badge=offer.period_human,
            title=f"{prod_name} ({offer.period_human})",
            subtitle=f"{offer.product} / {offer.offer_id}",
            is_checkout=True,
            requires_active_plan=False,
            default_no_tap=True,
            product_id=offer.product,
            offer_id=offer.offer_id,
            cta_label="Buka Checkout (Tinjau Manual)",
            summary="Membuka sheet checkout Google Play dengan verifikasi akun dan fase awal 0.",
            checklist=(),
            safety_note="Wajib tinjau langsung harga hari ini dan durasi di jendela Waydroid.",
        )
        dialog = CheckoutApprovalDialog(temp_step, self, lock_no_tap=True)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            self._append_log(f"Konfirmasi dibatalkan untuk {offer.product} ({offer.offer_id}).")
            return
        try:
            cmd = gui_core.build_custom_offer_command(
                offer.product,
                offer.offer_id,
                self.repo,
                confirmed=True,
            )
        except (OSError, ValueError) as exc:
            QtWidgets.QMessageBox.warning(self, "Tidak Dapat Membuka Checkout", str(exc))
            return
        self._launch_subprocess(
            cmd,
            kind="custom_offer",
            step_key=f"{offer.product} ({offer.offer_id})",
            is_checkout=True,
        )

    def _handle_custom_offer_finished(self, label: str, exit_code: int) -> None:
        if exit_code == 0:
            self.live_badge.setText("TINJAU")
            self.live_badge.setObjectName("BadgeWarn")
            self.live_badge.style().unpolish(self.live_badge)
            self.live_badge.style().polish(self.live_badge)
            self.live_status_text.setText(
                f"Sheet checkout {label} diproses (mode tinjau manual). "
                "Periksa harga hari ini Rp 0 dan durasi di Waydroid sebelum menekan Langganan."
            )
            QtWidgets.QMessageBox.information(
                self,
                "Tinjau Checkout di Waydroid",
                f"Sheet checkout untuk {label} sudah diproses dalam mode Tinjau Manual (--no-tap).\n\n"
                "Silakan periksa jendela Google Play di Waydroid:\n"
                "1. Pastikan total hari ini Rp 0 dan durasi sesuai.\n"
                "2. Klik Langganan / Subscribe secara manual bila sesuai.\n"
                "3. Cek status langganan di Google Play Subscriptions setelah selesai.",
            )
        else:
            self.live_badge.setText("GAGAL")
            self.live_badge.setObjectName("BadgeDanger")
            self.live_badge.style().unpolish(self.live_badge)
            self.live_badge.style().polish(self.live_badge)
            self.live_status_text.setText(
                f"Checkout {label} berhenti sebelum selesai. Lihat tab Log & Diagnostik."
            )

    # ---------- Window Close Safety ----------
    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self.is_busy():
            if self.active_is_checkout:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Checkout Sedang Berjalan",
                    "Tahap checkout Google Play sedang berjalan dan tidak boleh dihentikan paksa "
                    "agar status transaksi tidak menggantung. Tunggu hingga proses selesai.",
                )
                event.ignore()
                return
            self.stop_readonly_job()
            if self.active_process is not None:
                self.active_process.waitForFinished(2000)
        if self.env_worker is not None and self.env_worker.isRunning():
            self.env_worker.wait(1500)
        event.accept()


def main() -> int:
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("ePlus AI Toolkit")
    app.setDesktopFileName("argon-ai-toolkit")
    window = DesktopToolkitWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
