"""Linux and Fedora (Waydroid) port tests. All Android/checkout interactions are mocked."""
import base64
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch, MagicMock

import linux_runner
import waydroid_helper
from tui_core import command_for_step


class WaydroidHelperTests(unittest.TestCase):
    def test_parse_waydroid_status(self):
        mock_output = "Session:\tRUNNING\nVendor type:\tMAINLINE\n"
        with patch("waydroid_helper.shutil.which", return_value="/usr/bin/waydroid"), \
             patch("waydroid_helper.subprocess.run", return_value=type("Res", (), {"stdout": mock_output})()):
            status = waydroid_helper.get_waydroid_status()
            self.assertEqual(status.get("session"), "RUNNING")
            self.assertEqual(status.get("vendor type"), "MAINLINE")
            self.assertTrue(waydroid_helper.is_waydroid_running())

    def test_container_ip_from_lease_file(self):
        lease_data = "1794636986 00:16:3e:f9:d3:03 192.168.240.112 WayDroid-Device 01:00\n"
        with tempfile.NamedTemporaryFile("w+", delete=False) as tf:
            tf.write(lease_data)
            tf.flush()
            with patch.object(waydroid_helper, "WAYDROID_LEASE_FILE", Path(tf.name)):
                ip = waydroid_helper.get_waydroid_container_ip()
                self.assertEqual(ip, "192.168.240.112")

    def test_connect_waydroid_calls_adb(self):
        with patch("waydroid_helper.shutil.which", return_value="/usr/bin/adb"), \
             patch("waydroid_helper.is_waydroid_running", return_value=True), \
             patch("waydroid_helper.get_waydroid_container_ip", return_value="192.168.240.112"), \
             patch("waydroid_helper.subprocess.run") as mock_sub:
            mock_sub.return_value = type("Res", (), {"stdout": "connected to 192.168.240.112:5555"})()
            res = waydroid_helper.connect_waydroid("adb")
            self.assertEqual(res, "192.168.240.112:5555")


class LinuxStageAdapterTests(unittest.TestCase):
    def test_six_stage_mapping_and_no_force(self):
        offers = {
            2: ("pro12", "12months-eft", False),
            3: ("pro6", "6months-eft", True),
            4: ("pro6b", "6months-eft-2", True),
            5: ("pro6c", "6months-eft-ss-2026", True),
        }
        for step, (plan, expected, stacking) in offers.items():
            with self.subTest(step=step):
                cmd = linux_runner.stage_command(step, "192.168.240.112:5555", "alice@example.com", "python")
                self.assertEqual(cmd[cmd.index("--plan") + 1], plan)
                self.assertEqual(linux_runner.STAGES[step][1], expected)
                self.assertEqual("--stack" in cmd, stacking)
                self.assertIn("--no-switch", cmd)
                self.assertIn("--no-add", cmd)
                self.assertNotIn("--force", cmd)
        for step in (-1, 6, True, "2"):
            with self.assertRaises(ValueError):
                linux_runner.stage_command(step, "192.168.240.112:5555")
        for step in (2, 3, 4, 5):
            with self.assertRaises(ValueError):
                linux_runner.stage_command(step, "192.168.240.112:5555", "current@device")

    def test_list_never_opens_checkout(self):
        cmd = linux_runner.stage_command(1, "192.168.240.112:5555")
        for flag in ("--list", "--no-add", "--no-switch"):
            self.assertIn(flag, cmd)
        for forbidden in ("--force", "--stack", "--confirmed"):
            self.assertNotIn(forbidden, cmd)

    def test_preflight_auto_connects_waydroid_when_no_devices(self):
        with patch("linux_runner.shutil.which", return_value="/usr/bin/adb"), \
             patch("linux_runner.metadata.version", return_value="16.5.9"), \
             patch("linux_runner.online_serials", side_effect=[[], ["192.168.240.112:5555"]]), \
             patch("linux_runner.connect_waydroid") as mock_connect, \
             patch("linux_runner.auto_select_device", return_value="192.168.240.112:5555"):
            adb, serial = linux_runner.preflight()
            self.assertEqual(serial, "192.168.240.112:5555")
            mock_connect.assert_called_once()

    def test_tui_core_linux_passes_explicit_checkout_approval(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "linux_runner.py").write_text("# mock", encoding="utf-8")
            with patch("tui_core.sys.platform", "linux"):
                for step in range(6):
                    command = command_for_step(step, root)
                    self.assertEqual(command[0], sys.executable)
                    self.assertIn("linux_runner.py", command[1])
                    self.assertEqual(command[command.index("--step") + 1], str(step))
                    self.assertEqual("--confirmed" in command, step >= 2)
                    self.assertEqual("--active-confirmed" in command, step >= 3)


class LinuxTuiTests(unittest.IsolatedAsyncioTestCase):
    async def test_linux_tui_device_and_steps(self):
        from textual.widgets import Button, Select, Static
        from tui import GoogleAITUI
        with tempfile.TemporaryDirectory() as temp:
            with patch("tui.is_linux_platform", return_value=True), \
                 patch("tui.is_macos_platform", return_value=False):
                app = GoogleAITUI(repo=Path(temp), selected_step=1)
            with patch("tui.subprocess.Popen") as child:
                async with app.run_test(size=(100, 30)) as pilot:
                    self.assertEqual(app.query_one("#step", Select).value, 1)
                    device_text = app.query_one("#device", Static).render()
                    self.assertIn("Waydroid", str(device_text))
                    await pilot.pause()
                child.assert_not_called()


if __name__ == "__main__":
    unittest.main()
