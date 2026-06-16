#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

from git_push_utils import assess_repo, print_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Assess whether the current repository is ready to push to GitHub."
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Repository path. Defaults to the current working directory.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON only.",
    )
    return parser


def print_text_report(report: dict[str, object]) -> None:
    print(f"repo: {report['repo_path']}")
    print(f"github_remote_connected: {report['github_remote_connected']}")
    print(f"recommended_action: {report['recommended_action']}")
    print(f"safe_to_push: {report['safe_to_push']}")
    for reason in report["reasons"]:
        print(f"- {reason}")
    commands = report["commands"]
    if commands:
        print("next_commands:")
        for command in commands:
            print(f"  {command}")


def main() -> int:
    args = build_parser().parse_args()
    report = assess_repo(Path(args.repo))
    if args.json:
        print_json(report)
    else:
        print_text_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
