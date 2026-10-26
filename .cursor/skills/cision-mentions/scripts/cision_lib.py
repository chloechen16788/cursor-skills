#!/usr/bin/env python3
"""Cision mentions 导出的共享逻辑。请求头里的 token 只从环境变量读取，禁止写入日志。"""

from __future__ import annotations

import csv
import io
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

BASE_URL = "https://api.cision.one"
# Asia/Shanghai 无夏令时，固定 UTC+8。不用时区库，避免把窗口算成别的偏移。
SHANGHAI = timezone(timedelta(hours=8))
MAX_PAGE_SIZE = 4999
# page * page_size >= 5000 时接口返回 HTTP 400，响应体为空。5000 作为 page_size 同样如此。
MAX_PAGE_PRODUCT = 5000
MAX_PAGES = 200


def _quote(value: str, safe: str, encoding: str | None = None, errors: str | None = None) -> str:
    del safe, encoding, errors
    return quote(str(value), safe="")


def encode_query(params: dict) -> str:
    """百分号编码查询参数，使 filter[range][after] 这类括号键可被服务器还原。"""
    return urlencode(params, quote_via=_quote, safe="")


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def _http_error_message(status: int, body: bytes) -> str:
    if not body:
        return f"HTTP {status}，响应体为空"
    text = body.decode("utf-8", errors="replace")
    token = os.environ.get("CISION_API_TOKEN", "")
    if token and token in text:
        text = text.replace(token, "[REDACTED]")
    if len(body) > 400 or text.count(",") > 8:
        return f"HTTP {status}，响应体 {len(body)} 字节"
    line = " ".join(text.split())
    return f"HTTP {status}：{line[:300]}"


def api_get(path: str, query: str, accept: str) -> bytes:
    token = os.environ.get("CISION_API_TOKEN", "")
    if not token:
        raise RuntimeError("未设置环境变量 CISION_API_TOKEN")
    request = Request(
        f"{BASE_URL}{path}?{query}",
        method="GET",
        headers={
            "X-Auth-Token": token,
            "Accept": accept,
            "User-Agent": "cision-mentions-export",
        },
    )
    opener = build_opener(_NoRedirect)
    try:
        with opener.open(request, timeout=180) as response:
            return response.read()
    except HTTPError as error:
        raw = error.read() if error.fp is not None else b""
        raise RuntimeError(_http_error_message(error.code, raw)) from None
    except URLError as error:
        raise RuntimeError(f"请求失败：{error.reason}") from None


def normalize_stream_id(value: str) -> str:
    text = str(value).strip()
    if not text or any(ch not in "0123456789" for ch in text) or int(text) <= 0:
        raise RuntimeError("stream id 必须是正整数")
    return str(int(text))


def validate_page_size(page_size: int) -> int:
    if page_size < 1 or page_size > MAX_PAGE_SIZE:
        raise RuntimeError(
            f"pagination[page_size] 必须在 1 到 {MAX_PAGE_SIZE} 之间。"
            "5000 会返回 HTTP 400，且响应体为空"
        )
    return page_size


def shanghai_window(now: datetime | None = None) -> tuple[str, str]:
    """昨天 07:00（含）到今天 07:00（不含），按 Asia/Shanghai 日历日，再换成 UTC。"""
    if now is None:
        current = datetime.now(SHANGHAI)
    elif now.tzinfo is None:
        current = now.replace(tzinfo=SHANGHAI)
    else:
        current = now.astimezone(SHANGHAI)
    today = current.date()
    start = datetime(today.year, today.month, today.day, 7, 0, tzinfo=SHANGHAI) - timedelta(days=1)
    end = datetime(today.year, today.month, today.day, 7, 0, tzinfo=SHANGHAI)
    return _to_utc_z(start), _to_utc_z(end)


def _to_utc_z(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def mentions_query(after: str, before: str, page: int, page_size: int) -> str:
    return encode_query(
        {
            "format": "csv",
            "filter[range][after]": after,
            "filter[range][before]": before,
            "pagination[page]": page,
            "pagination[page_size]": page_size,
        }
    )


def parse_streams(payload: bytes) -> list[tuple[str, str]]:
    try:
        data = json.loads(payload.decode("utf-8-sig"))
    except json.JSONDecodeError as error:
        raise RuntimeError(f"streams 响应不是 JSON（{error}）") from None
    if isinstance(data, dict):
        keys = ",".join(sorted(str(key) for key in data.keys()))
        raise RuntimeError(f"streams 响应不是数组，对象键：{keys}")
    if not isinstance(data, list):
        raise RuntimeError("streams 响应不是数组")
    rows: list[tuple[str, str]] = []
    for item in data:
        if not isinstance(item, dict) or item.get("id") is None:
            continue
        label = str(item.get("label") or "")
        label = label.replace("\t", " ").replace("\r", " ").replace("\n", " ")
        rows.append((str(item["id"]), label))
    return rows


def fetch_streams() -> list[tuple[str, str]]:
    body = api_get("/public/api/v2/streams", encode_query({"format": "json"}), "application/json")
    return parse_streams(body)


def parse_csv_page(text: str, known_header: list[str] | None = None) -> tuple[list[str] | None, list[list[str]]]:
    cleaned = text.lstrip("\ufeff")
    if not cleaned.strip():
        return known_header, []
    parsed = [row for row in csv.reader(io.StringIO(cleaned)) if any(cell.strip() for cell in row)]
    if not parsed:
        return known_header, []
    if known_header is None:
        header = [cell.strip() for cell in parsed[0]]
        if "id" not in header:
            raise RuntimeError("首页 CSV 缺少 id 表头")
        return header, parsed[1:]
    first = [cell.strip() for cell in parsed[0]]
    if first == known_header:
        return known_header, parsed[1:]
    return known_header, parsed


def collect_pages(fetch_page, page_size: int, after: str, before: str) -> tuple[list[str], list[list[str]], int]:
    header: list[str] | None = None
    rows: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    pages_with_data = 0
    last_count = 0
    for page in range(1, MAX_PAGES + 1):
        if page * page_size >= MAX_PAGE_PRODUCT:
            # 4999 的满页已经覆盖接口允许的最大窗口。更小的 page_size 若本页已满，再请求会 400，不能静默截断。
            reached_end = pages_with_data and (last_count < page_size or page_size == MAX_PAGE_SIZE)
            if reached_end:
                print(
                    f"page={page} not_requested=page*page_size>={MAX_PAGE_PRODUCT}",
                    file=sys.stderr,
                )
                return header or ["id"], rows, pages_with_data
            raise RuntimeError(
                "下一页会使 page 与 page_size 的乘积达到 5000，接口返回 HTTP 400 且响应体为空"
            )
        page_header, data = parse_csv_page(fetch_page(page, page_size, after, before), header)
        if header is None:
            header = page_header or ["id"]
        print(f"page={page} data_rows={len(data)}", file=sys.stderr)
        if not data:
            return header, rows, pages_with_data
        signature = tuple(_row_id(header, row) for row in data)
        if signature in seen:
            raise RuntimeError(f"第 {page} 页与之前某一页的 id 序列相同，已停止")
        seen.add(signature)
        rows.extend(data)
        pages_with_data += 1
        last_count = len(data)
    raise RuntimeError(f"分页超过 {MAX_PAGES} 页，已停止")


def _row_id(header: list[str], row: list[str]) -> str:
    index = header.index("id")
    if index >= len(row):
        return ""
    return row[index].strip()


def select_delta(header: list[str], rows: list[list[str]], previous: set[str] | None) -> list[list[str]]:
    if previous is None:
        return list(rows)
    return [row for row in rows if not _row_id(header, row) or _row_id(header, row) not in previous]


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def load_previous_ids(path: Path) -> set[str] | None:
    if not path.exists():
        return None
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        try:
            header = [cell.strip() for cell in next(reader)]
        except StopIteration as error:
            raise RuntimeError(f"{path} 是空文件") from error
        if "id" not in header:
            raise RuntimeError(f"{path} 缺少 id 列")
        index = header.index("id")
        return {row[index].strip() for row in reader if index < len(row) and row[index].strip()}


def replace_file(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    temporary = dest.with_name(dest.name + ".tmp")
    temporary.write_bytes(src.read_bytes())
    os.replace(temporary, dest)


def default_output_dir() -> Path:
    raw = os.environ.get("CISION_OUTPUT_DIR", "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".local" / "share" / "cision-mentions"


def ensure_output_dir(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    toplevel = _git_toplevel(resolved)
    if toplevel is not None:
        try:
            resolved.relative_to(toplevel)
        except ValueError:
            pass
        else:
            raise RuntimeError(
                f"输出目录位于 git 仓库内（{resolved}）。"
                "请改到仓库外，默认是 ~/.local/share/cision-mentions"
            )
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _git_toplevel(path: Path) -> Path | None:
    probe = path if path.exists() else path.parent
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    try:
        output = subprocess.check_output(
            ["git", "-C", str(probe), "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None
    if not output:
        return None
    return Path(output).resolve()


def compact_stamp(value: str) -> str:
    return value.replace("-", "").replace(":", "").replace(".000", "")


def export_mentions(
    *,
    stream_id: str,
    output_dir: Path,
    fetch_page,
    now: datetime | None = None,
    page_size: int = MAX_PAGE_SIZE,
    push=None,
) -> dict:
    page_size = validate_page_size(page_size)
    stream_id = normalize_stream_id(stream_id)
    root = ensure_output_dir(Path(output_dir))
    after, before = shanghai_window(now)
    header, rows, pages = collect_pages(fetch_page, page_size, after, before)
    run_dir = root / "runs" / stream_id / f"{compact_stamp(after)}_{compact_stamp(before)}"
    full_path = run_dir / "full.csv"
    delta_path = run_dir / "delta.csv"
    latest_path = root / "state" / stream_id / "latest.csv"
    write_csv(full_path, header, rows)
    previous = load_previous_ids(latest_path)
    delta = select_delta(header, rows, previous)
    write_csv(delta_path, header, delta)
    summary = {
        "stream_id": stream_id,
        "after": after,
        "before": before,
        "pages": pages,
        "full_rows": len(rows),
        "previous_exists": previous is not None,
        "previous_ids": 0 if previous is None else len(previous),
        "delta_rows": len(delta),
        "full_csv": str(full_path),
        "delta_csv": str(delta_path),
        "latest_csv": str(latest_path),
    }
    if push is not None:
        push(delta_path, summary)
        summary["feishu"] = "sent" if delta else "sent_text"
    else:
        summary["feishu"] = "skipped"
    replace_file(full_path, latest_path)
    return summary


def fetch_mentions_page(stream_id: str, page: int, page_size: int, after: str, before: str) -> str:
    body = api_get(
        f"/public/api/v2/mentions/{normalize_stream_id(stream_id)}",
        mentions_query(after, before, page, page_size),
        "text/csv",
    )
    return body.decode("utf-8-sig")


def format_summary(summary: dict) -> str:
    previous = "yes" if summary["previous_exists"] else "no"
    lines = [
        f"stream_id={summary['stream_id']}",
        f"after={summary['after']}",
        f"before={summary['before']}",
        f"pages={summary['pages']}",
        f"full_rows={summary['full_rows']}",
        f"previous_exists={previous}",
        f"previous_ids={summary['previous_ids']}",
        f"delta_rows={summary['delta_rows']}",
        f"full_csv={summary['full_csv']}",
        f"delta_csv={summary['delta_csv']}",
        f"latest_csv={summary['latest_csv']}",
    ]
    if "bitable_written" in summary:
        lines.append(f"dedup={summary.get('dedup', 'bitable')}")
        lines.append(f"bitable_deleted={summary['bitable_deleted']}")
        lines.append(f"bitable_written={summary['bitable_written']}")
    lines.append(f"feishu={summary['feishu']}")
    return "\n".join(lines)
