import tempfile
import unittest
from pathlib import Path

from security_check import get_repo_files, scan_file

TEST_KEY_BODY_LENGTH = 32


class SecurityCheckTests(unittest.TestCase):
    def test_scan_file_flags_realistic_hardcoded_secret(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.py"
            test_api_key = "xai-" + ("a" * TEST_KEY_BODY_LENGTH)
            path.write_text(f'API_KEY = "{test_api_key}"\n', encoding="utf-8")
            findings = scan_file(path)
            self.assertTrue(findings)
            finding_types = [finding[1] for finding in findings]
            self.assertIn("XAI/OpenAI style API key", finding_types)

    def test_scan_file_ignores_placeholder_secret_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.py"
            path.write_text('api_key = "xai-your_key_here"\n', encoding="utf-8")
            findings = scan_file(path)
            self.assertEqual([], findings)

    def test_get_repo_files_uses_git_tracked_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tracked.py").write_text("print('ok')\n", encoding="utf-8")
            (root / "ignored.bin").write_bytes(b"\x00\x01")
            (root / "README").write_text("plain text without extension\n", encoding="utf-8")

            import subprocess

            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            subprocess.run(
                ["git", "add", "tracked.py", "ignored.bin", "README"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            files = get_repo_files(root)
            self.assertIn(root / "tracked.py", files)
            self.assertIn(root / "README", files)
            self.assertNotIn(root / "ignored.bin", files)


if __name__ == "__main__":
    unittest.main()
