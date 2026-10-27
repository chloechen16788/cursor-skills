#!/usr/bin/env python3
"""把增量 CSV 里的文章抓下来。标题用 CSV，正文保存 Firecrawl 的整段 markdown，再整表写入当日多维表格。"""

from __future__ import annotations

import csv
import os
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import cision_lib
import feishu_push

WIKI_NODE_TOKEN = "E3ABwkrHKiC6U4kdbKMcRRtdnYc"
TABLE_ID = "tblRwSj33U1e4t4N"
VIEW_ID = "vew0Gce8xU"
DAILY_WIKI_URL = (
    "https://prnewswire.feishu.cn/wiki/E3ABwkrHKiC6U4kdbKMcRRtdnYc"
    "?table=tblRwSj33U1e4t4N&view=vew0Gce8xU"
)
FIELD_NAMES = ("id", "url", "标题", "正文", "错误")
CELL_LIMIT = 100000
BITABLE_API = "https://open.feishu.cn/open-apis/bitable/v1"
WIKI_NODE_URL = "https://open.feishu.cn/open-apis/wiki/v2/spaces/get_node"


def missing_firecrawl_message() -> str:
    return (
        "未设置 FIRECRAWL_API_KEY。请用户添加该密钥后再跑正文。已停止，未删除飞书记录。"
    )


def firecrawl_key_present() -> bool:
    return bool(os.environ.get("FIRECRAWL_API_KEY", "").strip())


def gate_message() -> str | None:
    """密钥或命令缺失时返回错误文案。调用方必须在删除飞书记录之前停住。"""
    if not firecrawl_key_present():
        return missing_firecrawl_message()
    if shutil.which("firecrawl") is None:
        return "找不到 firecrawl 命令。已停止，未删除飞书记录。"
    return None


def load_delta(path: Path) -> tuple[list[str], list[list[str]]]:
    if not path.is_file():
        raise RuntimeError(f"找不到增量 CSV：{path}")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        try:
            header = [cell.strip() for cell in next(reader)]
        except StopIteration as error:
            raise RuntimeError(f"{path} 是空文件") from error
        return header, list(reader)


def _cell(header: list[str], row: list[str], name: str) -> str:
    if name not in header:
        return ""
    index = header.index(name)
    if index >= len(row):
        return ""
    return row[index].strip()


def unique_by_url(header: list[str], rows: list[list[str]]) -> list[dict]:
    if "url" not in header:
        raise RuntimeError("增量 CSV 缺少 url 列，未删除记录")
    seen: set[str] = set()
    items: list[dict] = []
    for row in rows:
        if not any(cell.strip() for cell in row):
            continue
        url = _cell(header, row, "url")
        if url:
            if url in seen:
                continue
            seen.add(url)
        items.append(
            {
                "id": _cell(header, row, "id"),
                "url": url,
                "csv_title": _cell(header, row, "title"),
            }
        )
    return items


def after_from_delta_path(path: Path) -> str:
    head = path.parent.name.split("_", 1)[0]
    tail = head[9:15]
    if (
        len(head) != 16
        or head[8] != "T"
        or not head.endswith("Z")
        or not (head[:8] + tail).isdigit()
    ):
        raise RuntimeError("无法从增量路径得到窗口起点，请传入 --after。未删除记录")
    return f"{head[0:4]}-{head[4:6]}-{head[6:8]}T{head[9:11]}:{head[11:13]}:{head[13:15]}.000Z"


def shanghai_data_date(after: str) -> str:
    try:
        moment = datetime.strptime(after, "%Y-%m-%dT%H:%M:%S.000Z").replace(
            tzinfo=timezone.utc
        )
    except ValueError as error:
        raise RuntimeError(f"窗口起点无法解析，未删除记录：{after}") from error
    return moment.astimezone(cision_lib.SHANGHAI).date().isoformat()


def daily_notice(data_date: str) -> str:
    return f"{data_date}\n{DAILY_WIKI_URL}"


def _limit_cells(record: dict) -> dict:
    notes: list[str] = []
    for key in ("标题", "正文"):
        value = record.get(key) or ""
        if len(value) > CELL_LIMIT:
            record[key] = value[:CELL_LIMIT]
            notes.append(f"{key}超过 {CELL_LIMIT} 字，已按飞书上限截断")
    if notes:
        extra = "；".join(notes)
        record["错误"] = (
            extra if not record.get("错误") else f"{record['错误']}；{extra}"
        )
    return record


def build_record(item: dict, fetched: dict | None) -> dict:
    """标题只用 CSV。正文保存 Firecrawl markdown，不交给模型改写。"""
    record = {
        "id": item.get("id") or "",
        "url": item.get("url") or "",
        "标题": item.get("csv_title") or "",
        "正文": "",
        "错误": "",
    }
    if not record["url"]:
        record["错误"] = "缺少 url"
        return record
    if not fetched:
        record["错误"] = "没有抓取结果"
        return record
    error = str(fetched.get("error") or "").strip()
    markdown = str(fetched.get("markdown") or "")
    if error:
        record["错误"] = feishu_push.redact_secrets(error)[:500]
        return record
    if not markdown.strip():
        record["错误"] = "抓取结果为空"
        return record
    record["正文"] = markdown
    record["错误"] = ""
    return _limit_cells(record)


def _data_rows(rows: list[list[str]]) -> list[list[str]]:
    return [row for row in rows if any(cell.strip() for cell in row)]


def scrape_one(url: str, dest: Path) -> dict:
    if dest.exists():
        dest.unlink()
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            ["firecrawl", "scrape", "--only-main-content", "-o", str(dest), url],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(dest.parent),
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"markdown": "", "error": "抓取超时"}
    if proc.returncode != 0:
        detail = (
            proc.stderr or proc.stdout or f"firecrawl exit {proc.returncode}"
        ).strip()
        detail = feishu_push.redact_secrets(detail)[:500]
        return {"markdown": "", "error": detail or f"firecrawl exit {proc.returncode}"}
    text = dest.read_text(encoding="utf-8", errors="replace") if dest.is_file() else ""
    if not text.strip():
        text = proc.stdout or ""
    if not text.strip():
        return {"markdown": "", "error": "抓取结果为空"}
    return {"markdown": text, "error": ""}


def scrape_urls(urls: list[str], workdir: Path, workers: int = 8) -> dict[str, dict]:
    if workers < 1 or workers > 20:
        raise RuntimeError("workers 必须在 1 到 20 之间")
    workdir.mkdir(parents=True, exist_ok=True)
    if not urls:
        return {}

    def job(index: int, url: str) -> tuple[str, dict]:
        return url, scrape_one(url, workdir / f"{index}.md")

    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=min(workers, len(urls))) as pool:
        futures = [pool.submit(job, index, url) for index, url in enumerate(urls)]
        for future in futures:
            url, result = future.result()
            results[url] = result
    return results


class DailyTable:
    """当日表。bitable 路径只用 get_node 返回的 obj_token。"""

    def __init__(self, request=None, token: str | None = None) -> None:
        self._request = request
        self._token = token or ""
        self.obj_token = ""

    def _call(self, url: str, method: str, payload: dict | None = None) -> dict:
        request = self._request or feishu_push.api_request
        if not self._token:
            self._token = feishu_push.tenant_token()
        return request(url, method, payload, self._token)

    def resolve(self) -> str:
        url = f"{WIKI_NODE_URL}?{urlencode({'token': WIKI_NODE_TOKEN})}"
        body = self._call(url, "GET")
        node = (body.get("data") or {}).get("node") or {}
        if not isinstance(node, dict):
            raise RuntimeError("wiki 节点响应缺少 node，未删除记录")
        obj = str(node.get("obj_token") or "")
        if node.get("obj_type") != "bitable" or not obj:
            raise RuntimeError(
                f"wiki 节点不是多维表格（obj_type={node.get('obj_type')}），未删除记录"
            )
        self.obj_token = obj
        return obj

    def _table(self, suffix: str, query: dict | None = None) -> str:
        if not self.obj_token:
            raise RuntimeError("尚未解析 obj_token，未删除记录")
        url = f"{BITABLE_API}/apps/{self.obj_token}/tables/{TABLE_ID}{suffix}"
        if query:
            return url + "?" + urlencode(query)
        return url

    def _pages(self, suffix: str, page_size: int) -> list[dict]:
        found: list[dict] = []
        page_token = ""
        for _ in range(1000):
            query = {"page_size": page_size}
            if page_token:
                query["page_token"] = page_token
            data = self._call(self._table(suffix, query), "GET").get("data") or {}
            items = data.get("items")
            if items is None:
                items = []
            if not isinstance(items, list):
                raise RuntimeError("飞书列表不是数组")
            found.extend(item for item in items if isinstance(item, dict))
            if not data.get("has_more"):
                return found
            page_token = str(data.get("page_token") or "")
            if not page_token:
                return found
        raise RuntimeError("飞书分页没有结束")

    def list_field_names(self) -> list[str]:
        names: list[str] = []
        for item in self._pages("/fields", 100):
            name = item.get("field_name")
            if isinstance(name, str) and name:
                names.append(name)
        return names

    def create_field(self, name: str) -> None:
        self._call(self._table("/fields"), "POST", {"field_name": name, "type": 1})

    def list_record_ids(self) -> list[str]:
        return [
            str(item["record_id"])
            for item in self._pages("/records", feishu_push.BITABLE_BATCH)
            if item.get("record_id")
        ]

    def delete_records(self, record_ids: list[str]) -> None:
        for start in range(0, len(record_ids), feishu_push.BITABLE_BATCH):
            chunk = record_ids[start : start + feishu_push.BITABLE_BATCH]
            self._call(self._table("/records/batch_delete"), "POST", {"records": chunk})

    def create_records(self, field_rows: list[dict]) -> None:
        for start in range(0, len(field_rows), feishu_push.BITABLE_BATCH):
            chunk = [
                {"fields": fields}
                for fields in field_rows[start : start + feishu_push.BITABLE_BATCH]
            ]
            self._call(self._table("/records/batch_create"), "POST", {"records": chunk})

    def prepare(self) -> None:
        self.resolve()
        names = self.list_field_names()
        for name in FIELD_NAMES:
            if name not in names:
                self.create_field(name)
                names.append(name)

    def replace_all(self, rows: list[dict]) -> tuple[int, int]:
        record_ids = self.list_record_ids()
        self.delete_records(record_ids)
        self.create_records(rows)
        return len(record_ids), len(rows)


def run_bodies(
    *,
    header: list[str],
    rows: list[list[str]],
    after: str,
    scrape,
    client,
    send,
    secrets_ok: bool,
    secret_error: str = "",
) -> dict:
    data_rows = _data_rows(rows)
    if not data_rows:
        return {"bodies": "skipped", "delta_rows": 0, "feishu": "skipped"}
    if not secrets_ok:
        raise RuntimeError(secret_error or missing_firecrawl_message())
    data_date = shanghai_data_date(after)

    items = unique_by_url(header, data_rows)
    urls = [item["url"] for item in items if item["url"]]
    try:
        fetched = scrape(urls) if urls else {}
    except Exception as error:  # noqa: BLE001
        detail = feishu_push.redact_secrets(str(error))
        raise RuntimeError(f"抓取没有完成，未删除飞书记录：{detail}") from None
    if not isinstance(fetched, dict):
        raise RuntimeError("抓取结果不是按 url 索引的对象，未删除记录")

    records: list[dict] = []
    scraped_ok = 0
    scraped_failed = 0
    stored_ok = 0
    for item in items:
        result = None if not item["url"] else fetched.get(item["url"])
        if (
            not item["url"]
            or not result
            or result.get("error")
            or not str(result.get("markdown") or "").strip()
        ):
            scraped_failed += 1
        else:
            scraped_ok += 1
        record = build_record(item, result)
        if record["正文"]:
            stored_ok += 1
        records.append(record)

    try:
        client.prepare()
    except Exception as error:  # noqa: BLE001
        raise RuntimeError(f"准备当日表失败，未删除记录：{error}") from None
    try:
        deleted, written = client.replace_all(records)
    except Exception as error:  # noqa: BLE001
        raise RuntimeError(f"写入当日表失败，未发送群链接：{error}") from None

    notice = daily_notice(data_date)
    try:
        send(notice)
    except Exception as error:  # noqa: BLE001
        raise RuntimeError(
            f"当日表已写入 {written} 行，群消息发送失败：{error}"
        ) from None
    return {
        "bodies": "written",
        "delta_rows": len(data_rows),
        "unique_urls": len(urls),
        "data_date": data_date,
        "scraped_ok": scraped_ok,
        "scraped_failed": scraped_failed,
        "stored_ok": stored_ok,
        "body_rows": written,
        "bitable_deleted": deleted,
        "bitable_written": written,
        "feishu": "sent",
        "notice": notice,
    }


def format_body_summary(summary: dict) -> str:
    if summary.get("bodies") == "skipped":
        return "delta_rows=0\nbodies=skipped\nfeishu=skipped"
    return "\n".join(
        [
            f"delta_rows={summary['delta_rows']}",
            f"unique_urls={summary['unique_urls']}",
            f"data_date={summary['data_date']}",
            f"scraped_ok={summary['scraped_ok']}",
            f"scraped_failed={summary['scraped_failed']}",
            f"stored_ok={summary['stored_ok']}",
            f"body_rows={summary['body_rows']}",
            f"bitable_deleted={summary['bitable_deleted']}",
            f"bitable_written={summary['bitable_written']}",
            f"feishu={summary['feishu']}",
        ]
    )


def run_delta_file(
    delta_path: Path,
    *,
    after: str = "",
    workers: int = 8,
    workdir: Path | None = None,
) -> dict:
    header, rows = load_delta(delta_path)
    window = after.strip() or after_from_delta_path(delta_path)
    blocked = gate_message()
    owned = workdir is None
    directory = (
        Path(tempfile.mkdtemp(prefix="cision-bodies-")) if workdir is None else workdir
    )
    try:
        return run_bodies(
            header=header,
            rows=rows,
            after=window,
            scrape=lambda urls: scrape_urls(urls, directory, workers=workers),
            client=DailyTable(),
            send=feishu_push.send_text,
            secrets_ok=blocked is None,
            secret_error=blocked or "",
        )
    finally:
        if owned:
            shutil.rmtree(directory, ignore_errors=True)
