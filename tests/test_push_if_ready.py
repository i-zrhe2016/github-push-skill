from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "github-push-when-ready" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from push_if_ready import is_conventional_commit_message  # noqa: E402


class ConventionalCommitMessageTests(unittest.TestCase):
    def test_accepts_standard_headers(self) -> None:
        messages = [
            "feat: add guarded push",
            "fix(cli): reject missing pathspec",
            "refactor(push-flow)!: change readiness contract",
            "docs: explain commit format\n\nAdditional context.",
        ]

        for message in messages:
            with self.subTest(message=message):
                self.assertTrue(is_conventional_commit_message(message))

    def test_rejects_nonstandard_headers(self) -> None:
        messages = [
            "Add guarded push",
            "Feat: add guarded push",
            "fix(cli) reject missing colon",
            "fix: ",
            " fix: leading whitespace",
            "fix: trailing whitespace ",
        ]

        for message in messages:
            with self.subTest(message=message):
                self.assertFalse(is_conventional_commit_message(message))


if __name__ == "__main__":
    unittest.main()
