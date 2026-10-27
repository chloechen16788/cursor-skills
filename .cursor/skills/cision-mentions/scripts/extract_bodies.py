#!/usr/bin/env python3
"""抓取本次增量 CSV 的正文，清洗后整表写入当日多维表格。不读取比较表。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import body_extract


def main() -> None:
    parser = argparse.ArgumentParser(
        description="用本次增量 CSV 抓取正文并整表写入当日多维表格"
    )
    parser.add_argument("--delta-csv", required=True, help="同一次导出写出的 delta.csv")
    parser.add_argument(
        "--after",
        default="",
        help="导出摘要里的 after。省略时从 delta.csv 的父目录名还原",
    )
    parser.add_argument(
        "--workers", type=int, default=8, help="同时抓取的 URL 数，1 到 20"
    )
    args = parser.parse_args()
    summary = body_extract.run_delta_file(
        Path(args.delta_csv),
        after=args.after,
        workers=args.workers,
    )
    print(body_extract.format_body_summary(summary))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # noqa: BLE001
        print(str(error), file=sys.stderr)
        sys.exit(1)
