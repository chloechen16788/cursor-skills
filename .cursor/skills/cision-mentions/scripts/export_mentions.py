#!/usr/bin/env python3
"""按上海时间窗口导出一个 stream 的 mentions，并与上次全量去重。不调用 streams 列表。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cision_lib
import feishu_push


def run_export(
    *,
    stream_id: str,
    output_dir: Path,
    fetch_page,
    page_size: int,
    push_feishu: bool,
    now=None,
    sync=None,
) -> dict:
    stream_id = cision_lib.normalize_stream_id(stream_id)
    if stream_id == feishu_push.BITABLE_SYNC_STREAM_ID:
        if sync is None and not feishu_push.credentials_present():
            raise RuntimeError(feishu_push.missing_credentials_message())
        return _export_1017610(
            output_dir=output_dir,
            fetch_page=fetch_page,
            page_size=page_size,
            now=now,
            sync=sync or feishu_push.sync_1017610_baseline,
        )
    if push_feishu and not feishu_push.credentials_present():
        raise RuntimeError(feishu_push.missing_credentials_message())

    def push(delta_path: Path, summary: dict) -> None:
        feishu_push.push_delta(delta_path, summary)

    return cision_lib.export_mentions(
        stream_id=stream_id,
        output_dir=output_dir,
        fetch_page=fetch_page,
        page_size=page_size,
        now=now,
        push=push if push_feishu else None,
    )


def _export_1017610(*, output_dir: Path, fetch_page, page_size: int, now, sync) -> dict:
    page_size = cision_lib.validate_page_size(page_size)
    root = cision_lib.ensure_output_dir(Path(output_dir))
    after, before = cision_lib.shanghai_window(now)
    header, rows, pages = cision_lib.collect_pages(fetch_page, page_size, after, before)
    run_dir = root / "runs" / feishu_push.BITABLE_SYNC_STREAM_ID / f"{cision_lib.compact_stamp(after)}_{cision_lib.compact_stamp(before)}"
    full_path = run_dir / "full.csv"
    delta_path = run_dir / "delta.csv"
    cision_lib.write_csv(full_path, header, rows)
    summary = {
        "stream_id": feishu_push.BITABLE_SYNC_STREAM_ID,
        "after": after,
        "before": before,
        "pages": pages,
        "full_rows": len(rows),
        "previous_exists": False,
        "previous_ids": 0,
        "delta_rows": 0,
        "full_csv": str(full_path),
        "delta_csv": str(delta_path),
        "latest_csv": "unused",
        "feishu": "skipped",
    }
    return sync(header, rows, delta_path, summary)


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

    output_dir = Path(args.output_dir) if args.output_dir else cision_lib.default_output_dir()
    stream_id = cision_lib.normalize_stream_id(args.stream_id)

    def fetch_page(page: int, page_size: int, after: str, before: str) -> str:
        return cision_lib.fetch_mentions_page(stream_id, page, page_size, after, before)

    summary = run_export(
        stream_id=stream_id,
        output_dir=output_dir,
        fetch_page=fetch_page,
        page_size=args.page_size,
        push_feishu=args.push_feishu,
    )
    print(cision_lib.format_summary(summary))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # noqa: BLE001
        print(str(error), file=sys.stderr)
        sys.exit(1)
