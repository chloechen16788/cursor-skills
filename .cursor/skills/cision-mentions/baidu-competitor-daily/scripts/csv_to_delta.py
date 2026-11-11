#!/usr/bin/env python3
"""csv_to_delta.py — 把监测导出的 CSV 转成管线所需的 XLSX（delta 工作表）。

用法：
    python scripts/csv_to_delta.py --input delta.csv --out delta.xlsx [--sheet delta]

说明：
- 监测系统导出为 CSV 时没有 `content` 列，正文在 `transcript` 列；本脚本把
  transcript 映射为 content，以满足 filter3/curation 的字段约定。
- 其余列按原样写入，缺失列补空，保证列集合稳定。
"""

import argparse
import csv
import os

import openpyxl

REQUIRED = [
    "title",
    "source",
    "locationCountry",
    "languageCode",
    "url",
    "publishedAt",
    "excerpt",
    "keywords",
    "author",
    "content",
    "impactScore",
]
# CSV 中正文列的历史命名 -> content
BODY_ALIASES = ["content", "transcript", "body", "text", "fullText"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="原始 CSV")
    ap.add_argument("--out", required=True, help="输出 xlsx")
    ap.add_argument("--sheet", default="delta")
    args = ap.parse_args()

    with open(args.input, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        header = list(reader.fieldnames or [])
    if not rows:
        raise SystemExit(f"CSV 无数据行: {args.input}")

    body_col = next((c for c in BODY_ALIASES if c in header), None)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = args.sheet
    ws.append(REQUIRED)
    for r in rows:
        vals = []
        for col in REQUIRED:
            if col == "content" and body_col:
                v = r.get(body_col, "")
            else:
                v = r.get(col, "")
            vals.append(v if v is not None else "")
        ws.append(vals)
    wb.save(args.out)

    print(
        f"rows: {len(rows)} | body<-{body_col} | sheet={args.sheet} -> {os.path.abspath(args.out)}"
    )


if __name__ == "__main__":
    main()
