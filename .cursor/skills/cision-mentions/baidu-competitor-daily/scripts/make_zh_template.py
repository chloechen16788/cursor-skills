#!/usr/bin/env python3
"""make_zh_template.py — 百度竞品同业日报 · 翻译辅助。

读取 final.json，生成 zh_template.json —— 一个按 idx 排列的清单：
  [ {"idx":0, "media_kb":"...", "section":"...", "entity":"...", "en":"英文标题", "zh":""}, ... ]
人工把每条的 "zh" 填上中文标题，保存为 zh.json，交给上一级 publish_daily_report.py。
"""

import argparse
import json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--final", required=True)
    ap.add_argument("--out", default="zh_template.json")
    args = ap.parse_args()

    final = json.load(open(args.final))
    out = []
    for x in sorted(final, key=lambda i: i["idx"]):
        out.append(
            {
                "idx": x["idx"],
                "media_kb": x.get("media_kb", x["source"]),
                "section": x["section"],
                "entity": x["entity"],
                "en": x["title"],
                "zh": "",
            }
        )
    json.dump(out, open(args.out, "w"), ensure_ascii=False, indent=1)
    print(f"Wrote {len(out)} entries -> {args.out}")
    print('Fill the "zh" field for each entry, then save as zh.json.')


if __name__ == "__main__":
    main()
