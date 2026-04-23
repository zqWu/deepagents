#!/usr/bin/env python3
"""Minimal demo script for the search skill."""

from __future__ import annotations

import argparse


def main() -> int:
    parser = argparse.ArgumentParser(description="Demo search skill script.")
    parser.add_argument("--query", required=True, help="Search text.")
    args = parser.parse_args()
    print(f"[{args.query}] 重大新闻:发布最新版本 v1.11, 性能显著提高。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
