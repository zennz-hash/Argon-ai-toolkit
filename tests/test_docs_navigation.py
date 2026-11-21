"""Validate the Markdown documentation hub and repository overview layout."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
LOCALIZED = ("vi", "zh-CN", "ja", "ko", "es", "fr")
TOPIC_PAGES = (
    "docs/README.md", "docs/SAFETY.md", "docs/INSTALLATION.md",
    "docs/USAGE.md", "docs/TROUBLESHOOTING.md", "docs/PROJECT.md",
    "docs/MACOS-PREVIEW.md", "docs/DETAILED-GUIDE.md",
    "docs/ORIGINAL-STEPS.md", "docs/AUTHOR-NOTES.md",
    "docs/WINDOWS-SMOKE-TEST.md",
)
MD_LINK = re.compile(r"(?<!!)\[[^]]+\]\(([^)]+)\)")


class DocumentationNavigationTests(unittest.TestCase):
    def test_original_full_readme_structure_and_translations(self):
        source_file = (ROOT / "README.canonical.md") if (ROOT / "README.canonical.md").is_file() else (ROOT / "README.md")
        english = source_file.read_text(encoding="utf-8")
        self.assertGreater(len(english), 12000)
        for heading in ("## Disclaimer", "## Install and prepare",
                        "## macOS", "## Use the dashboard (recommended)",
                        "## PowerShell CLI (advanced)", "## Troubleshooting and results",
                        "## Community support and related projects", "## Credits"):
            with self.subTest(heading=heading):
                self.assertIn(heading, english)
        for lang in LOCALIZED:
            with self.subTest(locale=lang):
                original = ROOT / f"README.{lang}.md"
                translated = original.read_text(encoding="utf-8")
                self.assertGreater(len(translated), 5500)
                self.assertIn("## macOS", translated)
                self.assertIn("## 3.", translated)
                self.assertIn("## 4.", translated)
                self.assertIn("(docs/README.md)", translated)
                self.assertTrue((DOCS / "i18n" / f"README.{lang}.md").is_file())
        self.assertGreater((DOCS / "USAGE.md").stat().st_size, 3000)

    def test_documentation_hub_references_every_topic(self):
        hub = (DOCS / "README.md").read_text(encoding="utf-8")
        self.assertIn("[!CAUTION]", hub)
        self.assertIn("2–5", hub)
        self.assertIn("macOS", hub)
        for target in TOPIC_PAGES:
            with self.subTest(page=target):
                self.assertTrue((ROOT / target).is_file())
                if target != "docs/README.md":
                    self.assertIn(f"({Path(target).name})", hub)
        for lang in LOCALIZED:
            self.assertIn(f"(i18n/README.{lang}.md)", hub)

    def test_all_local_markdown_links_point_to_existing_files(self):
        locations = [ROOT / "README.md", ROOT / "README.en.md"]
        locations.extend(ROOT / f"README.{lang}.md" for lang in LOCALIZED)
        locations.extend(sorted(DOCS.rglob("*.md")))
        locations.extend((ROOT / "CONTRIBUTING.md", ROOT / "AGENTS.md"))
        for source in locations:
            text = source.read_text(encoding="utf-8")
            for target in MD_LINK.findall(text):
                if target.startswith(("https://", "http://", "mailto:", "#")):
                    continue
                relative = target.partition("#")[0]
                if not relative:
                    continue
                with self.subTest(source=str(source.relative_to(ROOT)), link=relative):
                    self.assertTrue((source.parent / relative).is_file())

    def test_windows_and_mac_installation_both_work_from_project_root(self):
        canonical = (ROOT / "README.canonical.md") if (ROOT / "README.canonical.md").is_file() else (ROOT / "README.md")
        readme = canonical.read_text(encoding="utf-8")
        self.assertIn("### Windows requirements", readme)
        self.assertIn("## macOS — Install and run", readme)
        self.assertEqual(readme.count("git clone https://github.com/hoangsvit/google-ai.git"), 2)
        self.assertIn(".\\run-all.ps1", readme)
        self.assertIn("sh run-macos.sh", readme)
        self.assertIn("brew install android-platform-tools", readme)
        self.assertIn("MuMuPlayer Pro", readme)
        self.assertNotIn("git switch dev", readme)
        mac = (DOCS / "MACOS-PREVIEW.md").read_text(encoding="utf-8")
        self.assertNotIn("git switch dev", mac)
        self.assertIn("Version availability", mac)
        self.assertIn("run-macos.sh", mac)
        for lang in LOCALIZED:
            with self.subTest(locale=lang):
                text = (ROOT / f"README.{lang}.md").read_text(encoding="utf-8")
                self.assertIn("Windows", text)
                self.assertIn("macOS", text)
                self.assertIn("sh run-macos.sh", text)
                self.assertIn(".\\run-all.ps1", text)
                self.assertEqual(text.count("git clone https://github.com/hoangsvit/google-ai.git"), 2)
                self.assertNotIn("git switch dev", text)

    def test_user_install_guides_never_require_switching_to_dev(self):
        pages = [
            ROOT / "README.md", ROOT / "README.en.md",
            DOCS / "README.md", DOCS / "INSTALLATION.md",
            DOCS / "MACOS-PREVIEW.md", DOCS / "TROUBLESHOOTING.md",
        ]
        pages.extend(ROOT / f"README.{lang}.md" for lang in LOCALIZED)
        pages.extend(DOCS / "i18n" / f"README.{lang}.md" for lang in LOCALIZED)
        for page in pages:
            with self.subTest(page=str(page.relative_to(ROOT))):
                text = page.read_text(encoding="utf-8")
                self.assertNotIn("git switch dev", text)
                self.assertNotIn("checkout dev", text)
                if page.name.startswith("README") and page.parent == ROOT:
                    self.assertNotIn("`dev`", text)
        project = (DOCS / "PROJECT.md").read_text(encoding="utf-8")
        self.assertIn("run-macos.sh", project)
        self.assertIn("run-all.ps1", project)

    def test_restored_readme_retains_detailed_commands_and_links(self):
        canonical = (ROOT / "README.canonical.md") if (ROOT / "README.canonical.md").is_file() else (ROOT / "README.md")
        readme = canonical.read_text(encoding="utf-8")
        self.assertIn("(docs/README.md)", readme)
        self.assertIn("(docs/SAFETY.md)", readme)
        self.assertIn("(docs/USAGE.md)", readme)
        self.assertIn("sh run-macos.sh", readme)
        self.assertIn("## PowerShell CLI (advanced)", readme)
        self.assertIn("## Troubleshooting and results", readme)
        self.assertIn("## Repository structure", readme)
        self.assertNotIn("git switch dev", readme)

    def test_shell_commands_and_setup_requirements_are_platform_specific(self):
        canonical = (ROOT / "README.canonical.md") if (ROOT / "README.canonical.md").is_file() else (ROOT / "README.md")
        overview = canonical.read_text(encoding="utf-8")
        hub = (DOCS / "README.md").read_text(encoding="utf-8")
        mac_guide = (DOCS / "MACOS-PREVIEW.md").read_text(encoding="utf-8")
        win_guide = (DOCS / "INSTALLATION.md").read_text(encoding="utf-8")
        self.assertIn("PowerShell is not required or used on macOS", overview)
        self.assertIn("Terminal (zsh/bash)", hub)
        self.assertIn("PowerShell 5.1+", hub)
        self.assertIn("sh run-macos.sh", hub)
        self.assertIn(r".\run-all.ps1", hub)
        self.assertIn("PowerShell is not needed", mac_guide)
        self.assertIn("python3", mac_guide)
        self.assertIn("adb devices", mac_guide)
        self.assertIn("This guide is for Windows only", win_guide)

        first_readme = "README.canonical.md" if (ROOT / "README.canonical.md").is_file() else "README.md"
        for path in (first_readme, "README.vi.md", "README.es.md",
                     "README.fr.md", "README.ja.md", "README.ko.md",
                     "README.zh-CN.md"):
            with self.subTest(readme=path):
                text = (ROOT / path).read_text(encoding="utf-8")
                mac_section = text.split("## macOS", 1)[1].split("## ", 1)[0]
                self.assertIn("sh run-macos.sh", mac_section)
                self.assertNotIn("```powershell", mac_section.lower())
                self.assertNotIn(r".\\run-all.ps1", mac_section)


if __name__ == "__main__":
    unittest.main()
