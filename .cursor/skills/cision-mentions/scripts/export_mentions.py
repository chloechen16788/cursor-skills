#!/usr/bin/env python3
"""按上海时间窗口导出一个 stream 的 mentions，并与上次全量去重。不调用 streams 列表。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cision_lib
import feishu_push


def main() -> None:
    parser = argparse.ArgumentParser(
        description="导出指定 stream 的 Cision mentions CSV，并写出相对上次全量的增量"
    )
    parser.add_argument("--stream-id", required=True, help="已有的 stream id，正整数")
    parser.add_argument(
        "--page-size",
        type=int,
        default=cision_lib.MAX_PAGE_SIZE,
        help="每页条数，最大 4999。不要用 5000",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="输出目录，必须在 git 仓库外。默认 ~/.local/share/cision-mentions，也可用环境变量 CISION_OUTPUT_DIR",
    )
    parser.add_argument(
        "--push-feishu",
        action="store_true",
        help="把增量 CSV 推到技能里写死的飞书群，不能改目标",
    )
    args = parser.parse_args()

    if args.push_feishu and not feishu_push.credentials_present():
        raise RuntimeError(feishu_push.missing_credentials_message())

    output_dir = Path(args.output_dir) if args.output_dir else cision_lib.default_output_dir()
    stream_id = cision_lib.normalize_stream_id(args.stream_id)

    def fetch_page(page: int, page_size: int, after: str, before: str) -> str:
        return cision_lib.fetch_mentions_page(stream_id, page, page_size, after, before)

    def push(delta_path: Path, summary: dict) -> None:
        feishu_push.push_delta(delta_path, summary)

    summary = cision_lib.export_mentions(
        stream_id=stream_id,
        output_dir=output_dir,
        fetch_page=fetch_page,
        page_size=args.page_size,
        push=push if args.push_feishu else None,
    )
    print(cision_lib.format_summary(summary))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # noqa: BLE001
        print(str(error), file=sys.stderr)
        sys.exit(1)
