"""Waydroid integration helper for Fedora and Linux.

Provides detection, status checking, and automatic ADB connectivity for Waydroid.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Optional

WAYDROID_LEASE_FILE = Path("/var/lib/misc/dnsmasq.waydroid0.leases")
DEFAULT_WAYDROID_IP = "192.168.240.112"


def is_waydroid_installed() -> bool:
    """Check if the waydroid command is available on host."""
    return shutil.which("waydroid") is not None


def get_waydroid_status() -> dict[str, str]:
    """Parse output of 'waydroid status'."""
    if not is_waydroid_installed():
        return {"session": "NOT_INSTALLED", "vendor": "UNKNOWN"}
    try:
        res = subprocess.run(["waydroid", "status"], capture_output=True, text=True, timeout=5)
        out = res.stdout
        status = {}
        for line in out.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                status[k.strip().lower()] = v.strip().upper()
        return status
    except (subprocess.TimeoutExpired, OSError):
        return {"session": "ERROR", "vendor": "UNKNOWN"}


def is_waydroid_running() -> bool:
    """Return True if Waydroid session is currently active/running."""
    status = get_waydroid_status()
    return status.get("session") == "RUNNING"


def get_waydroid_container_ip() -> Optional[str]:
    """Discover Waydroid container IP from dnsmasq lease file or network routes."""
    # 1. Read dnsmasq leases
    if WAYDROID_LEASE_FILE.is_file():
        try:
            content = WAYDROID_LEASE_FILE.read_text(encoding="utf-8", errors="ignore")
            for line in content.splitlines():
                parts = line.split()
                if len(parts) >= 3:
                    ip = parts[2]
                    if re.fullmatch(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip):
                        return ip
        except OSError:
            pass

    # 2. Check ARP cache / ip neigh on waydroid0
    try:
        res = subprocess.run(["ip", "neigh", "show", "dev", "waydroid0"],
                             capture_output=True, text=True, timeout=3)
        for line in res.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 1 and re.fullmatch(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", parts[0]):
                return parts[0]
    except (subprocess.TimeoutExpired, OSError):
        pass

    return DEFAULT_WAYDROID_IP if is_waydroid_running() else None


def connect_waydroid(adb: str = "adb") -> Optional[str]:
    """Attempt to establish ADB connection to the Waydroid container.

    Returns the connected serial (e.g. '192.168.240.112:5555') or None.
    """
    if not shutil.which(adb):
        return None

    # Check if waydroid session is running
    running = is_waydroid_running()

    # If internal VPN is active, ensure local subnet traffic routes to eth0
    if running:
        try:
            subprocess.run(["sudo", "waydroid", "shell"],
                           input="ip rule add to 192.168.240.0/24 lookup eth0 pref 1000 2>/dev/null || true\n",
                           capture_output=True, text=True, timeout=5)
        except Exception:
            pass

    # If waydroid is running, try 'waydroid adb connect' first
    if running and is_waydroid_installed():
        try:
            subprocess.run(["waydroid", "adb", "connect"],
                           capture_output=True, text=True, timeout=5)
        except (subprocess.TimeoutExpired, OSError):
            pass

    # Next attempt direct adb connect with discovered or default IP
    candidate_ips = []
    discovered_ip = get_waydroid_container_ip()
    if discovered_ip:
        candidate_ips.append(discovered_ip)
    if DEFAULT_WAYDROID_IP not in candidate_ips:
        candidate_ips.append(DEFAULT_WAYDROID_IP)

    for ip in candidate_ips:
        endpoint = f"{ip}:5555"
        try:
            res = subprocess.run([adb, "connect", endpoint],
                                 capture_output=True, text=True, timeout=5)
            if "connected to" in res.stdout.lower() or "already connected to" in res.stdout.lower():
                return endpoint
        except (subprocess.TimeoutExpired, OSError):
            continue

    return None
