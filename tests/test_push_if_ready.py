from __future__ import annotations

import sys
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from tempfile import TemporaryDirectory
from unittest.mock import patch


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "github-push-when-ready" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from push_if_ready import is_conventional_commit_message  # noqa: E402
from github_about import ensure_github_about, github_repo_slug, readme_description  # noqa: E402


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


class GithubAboutTests(unittest.TestCase):
    def test_parses_supported_github_remote_urls(self) -> None:
        urls = [
            "https://github.com/example/project.git",
            "git@github.com:example/project.git",
            "ssh://git@github.com/example/project",
        ]

        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(github_repo_slug(url), "example/project")

    def test_reads_first_prose_paragraph(self) -> None:
        with TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / "README.md").write_text(
                "# Project\n\nA concise project summary.\n\n## Details\n",
                encoding="utf-8",
            )
            self.assertEqual(readme_description(repo), "A concise project summary.")

    @patch("github_about.shutil.which", return_value="/usr/bin/gh")
    @patch(
        "github_about.load_remote_urls",
        return_value={"origin": {"push": "https://github.com/example/project.git"}},
    )
    @patch("github_about._run_gh")
    def test_fills_missing_description_and_verifies_it(
        self,
        run_gh,
        _load_remote_urls,
        _which,
    ) -> None:
        run_gh.side_effect = [
            CompletedProcess([], 0, "", ""),
            CompletedProcess([], 0, "", ""),
            CompletedProcess([], 0, "A concise project summary.", ""),
        ]
        with TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / "README.md").write_text(
                "# Project\n\nA concise project summary.\n",
                encoding="utf-8",
            )
            result = ensure_github_about(repo, "origin")

        self.assertTrue(result.ok)
        self.assertTrue(result.changed)
        self.assertEqual(result.description, "A concise project summary.")
        self.assertEqual(
            run_gh.call_args_list[1].args,
            ("repo", "edit", "example/project", "--description", "A concise project summary."),
        )


if __name__ == "__main__":
    unittest.main()
