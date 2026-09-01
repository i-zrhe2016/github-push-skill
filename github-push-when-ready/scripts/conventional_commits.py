#!/usr/bin/env python3

"""Validate commit messages against the Conventional Commits 1.0.0 header."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


# Conventional Commits 1.0.0 requires:
#   <type>[optional scope][!]: <description>
# Types are lowercase nouns. A scope is non-empty, may contain internal spaces,
# and does not contain parentheses; the body and footers remain free-form as the
# specification allows.
CONVENTIONAL_COMMIT_HEADER = re.compile(
    r"^[a-z][a-z0-9-]*(?:\(([^\s()](?:[^()\r\n]*[^\s()])?)\))?!?: (\S(?:.*\S)?)$"
)


def is_conventional_commit_message(message: str) -> bool:
    """Return whether the first line has the required Conventional Commit form."""
    header = message.splitlines()[0] if message else ""
    return bool(CONVENTIONAL_COMMIT_HEADER.fullmatch(header))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a commit message using Conventional Commits 1.0.0."
    )
    parser.add_argument("message_file", type=Path, help="Path to Git's commit message file.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        message = args.message_file.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        print(f"unable to read commit message: {error}")
        return 1

    if is_conventional_commit_message(message):
        return 0

    print(
        "commit message must follow Conventional Commits 1.0.0: "
        "<type>[optional scope][!]: <description>"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
