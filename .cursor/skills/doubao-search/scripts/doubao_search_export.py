#!/usr/bin/env python3
import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from openpyxl import Workbook

API_URL = "https://open.feedcoopapi.com/search_api/web_search"
FIELD_SPECS = [
    ("标题", "Title"),
    ("相关摘要", "Summary"),
    ("媒体/站点", "SiteName"),
    ("链接", "Url"),
    ("发布时间", "PublishTime"),
    ("正文", "Content"),
    ("权威度描述", "AuthInfoDes"),
    ("权威度等级", "AuthInfoLevel"),
]

DATE_RANGE_RE = re.compile(
    r"(?P<start_month>\d{1,2})\s*[./月]\s*(?P<start_day>\d{1,2})\s*[-~—到至]\s*"
    r"(?P<end_month>\d{1,2})\s*[./月]\s*(?P<end_day>\d{1,2})"
)


def read_env_value(env_path: Path, key: str) -> str:
    if not env_path.exists():
        raise RuntimeError(f"{env_path} 不存在")
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith(f"{key}="):
            value = line.split("=", 1)[1].strip()
            if value:
                return value
    raise RuntimeError(f"{key} 未在 {env_path} 中配置")


def call_doubao_search(api_key: str, query: str) -> dict:
    payload = {
        "Query": query,
        "SearchType": "web",
        "Count": 30,
        "Filter": {"NeedContent": True, "NeedUrl": True},
        "QueryControl": {"QueryRewrite": True},
    }
    req = Request(
        API_URL,
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
    )
    try:
        with urlopen(req, timeout=90) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            data = json.loads(body)
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {error.code}: {detail}") from error
    except Exception as error:  # noqa: BLE001
        raise RuntimeError(f"请求失败: {error}") from error

    meta_error = (data.get("ResponseMetadata") or {}).get("Error")
    if meta_error:
        raise RuntimeError(f"接口返回错误: {meta_error}")
    return data


def parse_query_date_range(query: str, year: int) -> tuple[date, date] | None:
    match = DATE_RANGE_RE.search(query)
    if not match:
        return None
    try:
        start = date(year, int(match.group("start_month")), int(match.group("start_day")))
        end = date(year, int(match.group("end_month")), int(match.group("end_day")))
    except ValueError:
        return None

    if end < start:
        end = date(year + 1, end.month, end.day)
    return start, end


def parse_publish_date(raw_publish_time: str, fallback_year: int) -> date | None:
    text = (raw_publish_time or "").strip()
    if not text:
        return None

    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        pass

    md_match = re.search(r"(?P<month>\d{1,2})[./月](?P<day>\d{1,2})", text)
    if md_match:
        try:
            return date(fallback_year, int(md_match.group("month")), int(md_match.group("day")))
        except ValueError:
            return None
    return None


def in_date_range(publish_time: str, query_range: tuple[date, date] | None, fallback_year: int) -> bool:
    if query_range is None:
        return True
    publish_date = parse_publish_date(publish_time, fallback_year)
    if publish_date is None:
        return False
    start, end = query_range
    return start <= publish_date <= end


def build_rows(items: list[dict], query_range: tuple[date, date] | None, fallback_year: int) -> list[dict]:
    rows = []
    for item in items:
        title = (item.get("Title") or "").strip()
        if not title:
            continue
        if not in_date_range(item.get("PublishTime", ""), query_range, fallback_year):
            continue
        row = {}
        for _, en in FIELD_SPECS:
            if en == "Summary":
                row[en] = item.get("Summary") or item.get("Snippet") or ""
            else:
                row[en] = item.get(en, "")
        rows.append(row)
    return rows


def export_excel(rows: list[dict], out_path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "doubao_search"
    ws.append([f"{zh} ({en})" for zh, en in FIELD_SPECS])
    for row in rows:
        ws.append([row.get(en, "") for _, en in FIELD_SPECS])

    widths = {"A": 42, "B": 64, "C": 20, "D": 54, "E": 24, "F": 72, "G": 18, "H": 18}
    for col, width in widths.items():
        ws.column_dimensions[col].width = width
    wb.save(out_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Doubao Search export tool")
    parser.add_argument("--query", action="append", required=True, help="Search query (repeatable)")
    parser.add_argument("--max-workers", type=int, default=3, help="Parallel worker count")
    parser.add_argument("--env-file", default=".env", help="Path to .env file")
    parser.add_argument("--out-dir", default="Doc", help="Output directory")
    args = parser.parse_args()

    env_path = Path(args.env_file).resolve()
    api_key = read_env_value(env_path, "DOUBAO_API_KEY")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    xlsx_path = out_dir / f"doubao_search_export_{stamp}.xlsx"
    raw_path = out_dir / f"doubao_search_export_{stamp}.json"

    current_year = datetime.now().year
    all_rows: list[dict] = []
    raw_bundle: dict = {"queries": args.query, "results": []}

    with ThreadPoolExecutor(max_workers=max(1, args.max_workers)) as pool:
        fut_map = {pool.submit(call_doubao_search, api_key, q): q for q in args.query}
        for fut in as_completed(fut_map):
            query = fut_map[fut]
            try:
                data = fut.result()
                items = (data.get("Result") or {}).get("WebResults") or []
                query_range = parse_query_date_range(query, current_year)
                rows = build_rows(items, query_range, current_year)
                for row in rows:
                    row["__query"] = query
                all_rows.extend(rows)
                raw_bundle["results"].append({"query": query, "ok": True, "data": data, "row_count": len(rows)})
                print(f"[OK] {query} -> {len(rows)} rows")
            except Exception as error:  # noqa: BLE001
                raw_bundle["results"].append({"query": query, "ok": False, "error": str(error)})
                print(f"[ERR] {query} -> {error}")

    seen_titles: set[str] = set()
    dedup_rows: list[dict] = []
    for row in all_rows:
        title_key = (row.get("Title") or "").strip().lower()
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        row.pop("__query", None)
        dedup_rows.append(row)

    export_excel(dedup_rows, xlsx_path)
    raw_path.write_text(json.dumps(raw_bundle, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"excel={xlsx_path}")
    print(f"raw={raw_path}")
    print(f"total_rows={len(dedup_rows)}")


if __name__ == "__main__":
    main()
