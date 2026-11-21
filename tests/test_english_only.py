"""Keep maintained source and filenames free of non-English scripts.

Known non-English Android UI labels remain in the Python runtime as Unicode
escapes; user-visible CLI text and source comments are in English.
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "__pycache__", "node_modules", "ultra0-report", ".venv", "venv"}
EXTS = {".py", ".js", ".mjs", ".ps1", ".bat", ".md", ".txt", ".yml", ".yaml"}
SCRIPT_RANGES = ((0x3400, 0x9FFF), (0x3040, 0x30FF), (0xAC00, 0xD7AF))
LOCALIZED_READMES = {f"README.{locale}.md" for locale in ("vi", "zh-CN", "ja", "ko", "es", "fr")}


def has_non_english_script(text):
    return any(start <= ord(char) <= end for char in text
               for start, end in SCRIPT_RANGES)


class EnglishOnlyTest(unittest.TestCase):
    def test_filenames_are_english_only(self):
        bad = []
        for file in ROOT.rglob("*"):
            if any(part in SKIP_DIRS for part in file.relative_to(ROOT).parts):
                continue
            if has_non_english_script(str(file.relative_to(ROOT))):
                bad.append(str(file.relative_to(ROOT)))
        self.assertEqual([], bad, "Rename non-English file or directory names")

    def test_source_files_are_english_only(self):
        bad = []
        for file in ROOT.rglob("*"):
            if not file.is_file() or file.suffix.lower() not in EXTS:
                continue
            if any(part in SKIP_DIRS for part in file.relative_to(ROOT).parts):
                continue
            if file.name in LOCALIZED_READMES and file.parent in (
                ROOT, ROOT / "docs" / "i18n"
            ):
                continue  # Intentionally translated overviews and detailed guides.
            content = file.read_text(encoding="utf-8")
            if file.parent == ROOT and file.name == "README.md":
                # Allow native-language names only in the English README switcher.
                content = "\n".join(line for line in content.splitlines()
                                    if not line.startswith("**Languages:**"))
            if has_non_english_script(content):
                bad.append(str(file.relative_to(ROOT)))
        self.assertEqual([], bad, "Translate comments, documentation and CLI strings")


if __name__ == "__main__":
    unittest.main()
