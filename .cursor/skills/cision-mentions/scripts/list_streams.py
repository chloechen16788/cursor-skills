#!/usr/bin/env python3
"""列出 Cision Mention Stream 的 id 和 label。不请求 mentions。"""

from __future__ import annotations

import argparse
import sys

import cision_lib


def main() -> None:
    parser = argparse.ArgumentParser(description="列出 Cision Mention Stream 的 id 和 label")
    parser.parse_args()
    for stream_id, label in cision_lib.fetch_streams():
        print(f"{stream_id}\t{label}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # noqa: BLE001
        print(str(error), file=sys.stderr)
        sys.exit(1)
