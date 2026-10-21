"""Unit tests for the hello.txt factory verification artifact.

Standard-library only: run with

    python3 -m unittest discover -s tests -t . -v
"""

import pathlib
import unittest

EXPECTED_CONTENT = "Fusion factory verification complete"

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
HELLO_TXT = REPO_ROOT / "hello.txt"


class TestHelloTxt(unittest.TestCase):
    def test_hello_txt_exists(self):
        self.assertTrue(
            HELLO_TXT.is_file(),
            f"expected factory verification file at {HELLO_TXT}",
        )

    def test_hello_txt_content_is_exact(self):
        self.assertTrue(
            HELLO_TXT.is_file(),
            f"expected factory verification file at {HELLO_TXT}",
        )
        content = HELLO_TXT.read_text(encoding="utf-8")
        self.assertEqual(content.strip(), EXPECTED_CONTENT)

    def test_hello_txt_has_single_line(self):
        self.assertTrue(
            HELLO_TXT.is_file(),
            f"expected factory verification file at {HELLO_TXT}",
        )
        content = HELLO_TXT.read_text(encoding="utf-8")
        non_empty_lines = [line for line in content.splitlines() if line.strip()]
        self.assertEqual(len(non_empty_lines), 1)


if __name__ == "__main__":
    unittest.main()
