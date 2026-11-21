"""Set up Python, Frida and ADB for the Google AI Android toolkit.

Steps:
    1. Check the installed Python version.
    2. Install the pinned Frida 16.5.9 build used by this implementation.
    3. Locate ADB (environment, PATH, MuMu) or download platform-tools.
    4. Connect the emulator and run ultra0.py --check.

Usage: run setup-environment.bat or python setup_env.py.
"""
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from device_selector import auto_select_device, online_serials

BASE = Path(__file__).resolve().parent
ADB_CANDIDATES = [
    os.environ.get("ADB_PATH", ""),
    r"C:\Program Files\Netease\MuMuPlayer-12.0\shell\adb.exe",
    r"C:\Program Files\Netease\MuMuPlayerGlobal-12.0\shell\adb.exe",
    r"C:\Program Files (x86)\Netease\MuMuPlayer-12.0\shell\adb.exe",
    r"D:\Program Files\Netease\MuMu\nx_main\adb.exe",
    r"D:\Program Files\Netease\MuMu\nx_device\12.0\shell\adb.exe",
    r"C:\Program Files\Netease\MuMu\nx_main\adb.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"),
    os.path.expandvars(r"%USERPROFILE%\AppData\Local\Android\Sdk\platform-tools\adb.exe"),
]
PLATFORM_TOOLS_URL = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"


def step(msg):
    print(f"\n▶ {msg}", flush=True)


def ok(msg):
    print(f"   ✅ {msg}", flush=True)


def warn(msg):
    print(f"   ⚠️  {msg}", flush=True)


def die(msg):
    print(f"\n❌ {msg}", flush=True)
    sys.exit(1)


def check_python():
    step("Checking Python")
    v = sys.version_info
    print(f"   {platform.python_version()}  ({platform.architecture()[0]})")
    if v < (3, 9):
        die("Python is too old; install Python 3.10 or newer: https://www.python.org/downloads/")
    ok("Python is available")


def install_frida():
    step("Installing pinned Frida 16.5.9")
    try:
        import frida
        if frida.__version__ == "16.5.9":
            ok(f"Frida {frida.__version__} is already installed")
            return
        warn(f"Current Frida is {frida.__version__}; switching to pinned 16.5.9...")
    except Exception:
        pass

    cmds = [
        [sys.executable, "-m", "pip", "install", "--no-cache-dir", "frida==16.5.9"],
        [sys.executable, "-m", "pip", "install", "--no-cache-dir",
         "-i", "https://pypi.tuna.tsinghua.edu.cn/simple", "frida==16.5.9"],
    ]
    for c in cmds:
        print("   " + " ".join(c[2:]))
        r = subprocess.run(c, capture_output=True, text=True, errors="ignore")
        if r.returncode == 0:
            break
        print("   " + (r.stderr or r.stdout).strip().splitlines()[-1][:160])
    try:
        import importlib
        import frida
        importlib.reload(frida)
        ok(f"Frida {frida.__version__} installed")
    except Exception as e:
        die(f"Failed to install Frida: {e}\n   Run: pip install frida==16.5.9")


def adb_is_working(adb: Path | str) -> bool:
    """Verify a file actually runs as ADB (not a partial installation)."""
    path = Path(adb)
    if not path.is_file():
        return False
    try:
        result = subprocess.run([str(path), "version"], capture_output=True,
                                text=True, timeout=10, errors="replace")
        return result.returncode == 0 and "Android Debug Bridge" in result.stdout
    except (OSError, subprocess.TimeoutExpired):
        return False


def user_platform_tools() -> Path:
    """Store a fallback copy under the current user's writable profile."""
    parent = os.environ.get("LOCALAPPDATA")
    return (Path(parent) if parent else Path.home() / ".cache") / "google-ai" / "platform-tools"


def download_platform_tools() -> str:
    """Do not extract over an adb.exe that Windows may currently have locked."""
    preferred = BASE / "platform-tools"
    fallback = user_platform_tools()
    for directory in (preferred, fallback):
        adb = directory / "adb.exe"
        if adb_is_working(adb):
            ok(f"Reusing existing Android platform-tools: {adb}")
            return str(adb)

    step("Downloading official Android platform-tools")
    try:
        with tempfile.TemporaryDirectory(prefix="google-ai-platform-tools-") as temp_dir:
            temp_root = Path(temp_dir)
            archive = temp_root / "platform-tools.zip"
            with urllib.request.urlopen(PLATFORM_TOOLS_URL, timeout=180) as response, open(archive, "wb") as target:
                shutil.copyfileobj(response, target)
            with zipfile.ZipFile(archive) as z:
                if "platform-tools/adb.exe" not in z.namelist():
                    raise RuntimeError("Official platform-tools archive did not contain adb.exe")
                z.extractall(temp_root)
            source = temp_root / "platform-tools"

            for target in (preferred, fallback):
                try:
                    shutil.copytree(source, target, dirs_exist_ok=True)
                    adb = target / "adb.exe"
                    if adb_is_working(adb):
                        ok(f"Android platform-tools installed: {adb}")
                        return str(adb)
                    warn(f"ADB could not run from {target}; trying another location.")
                except OSError as exc:
                    warn(f"Cannot update {target}: {exc}. Trying the per-user location.")
    except (OSError, zipfile.BadZipFile, RuntimeError, TimeoutError) as exc:
        die(f"Could not install Android platform-tools: {exc}. "
            "Install the official package from "
            "https://developer.android.com/tools/releases/platform-tools "
            "or set ADB_PATH to an existing adb.exe.")

    die("ADB is still unusable. Close processes locking adb.exe, "
        "or set ADB_PATH to a working SDK platform-tools installation.")


def find_adb() -> str:
    step("Locating ADB")
    candidates = [
        os.environ.get("ADB_PATH", ""),
        shutil.which("adb") or "",
        "/usr/bin/adb",
        "/usr/local/bin/adb",
        str(BASE / "platform-tools" / "adb.exe"),
        str(user_platform_tools() / "adb.exe"),
        *ADB_CANDIDATES,
    ]
    for candidate in candidates:
        if candidate and adb_is_working(candidate):
            ok(f"Using existing ADB: {candidate}")
            return str(candidate)
    warn("No usable ADB installation found; downloading official platform-tools.")
    return download_platform_tools()


def connect_emulator(adb):
    """Select an existing Android device; do not connect all emulator ports."""
    step("Connecting to the emulator")
    devices = online_serials(adb)
    if not devices:
        try:
            from waydroid_helper import connect_waydroid
            connect_waydroid(adb)
            devices = online_serials(adb)
        except Exception:
            pass
    if not devices:
        for port in ("16384", "7555", "16416", "21503", "62001", "5555"):
            subprocess.run([adb, "connect", f"127.0.0.1:{port}"],
                           capture_output=True, text=True, errors="replace", timeout=10)
            devices = online_serials(adb)
            if devices:
                break
    if not devices:
        warn("No online Android device. Start Waydroid or emulator, and enable ADB debugging.")
        return None
    selected = auto_select_device(adb, serials=devices)
    if not selected:
        warn("Multiple distinct devices are available. Specify -Serial in run-all.ps1.")
        print("   Devices: " + ", ".join(devices))
        return None
    if len(devices) > 1:
        ok(f"Auto-selected device {selected} among {', '.join(devices)}")
    else:
        ok(f"Connected device: {selected}")
    return selected


def run_check(adb, serial):
    step("Running environment preflight (ultra0.py --check)")
    env = dict(os.environ)
    env["ADB_PATH"] = adb
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([sys.executable, "ultra0.py", "--check", "--serial", serial], cwd=str(BASE),
                       env=env, capture_output=True, encoding="utf-8", errors="ignore")
    print(r.stdout.strip() or r.stderr.strip())
    return r.returncode == 0


def main():
    print("=" * 60)
    print("  Google AI Android toolkit - Environment setup")
    print("=" * 60)
    check_python()
    install_frida()
    adb = find_adb()
    os.environ["ADB_PATH"] = str(adb)
    serial = connect_emulator(adb)

    if serial:
        good = run_check(adb, serial)
        print("\n" + "=" * 60)
        if good:
            print("  Environment ready. Next, run: .\\run-all.ps1 -ListOnly")
        else:
            print("  Environment check incomplete. Inspect warnings above; Play Store may not be running.")
        print("=" * 60)
    else:
        print("\nStart MuMu, enable ADB debugging, and rerun this setup script.")


if __name__ == "__main__":
    main()
