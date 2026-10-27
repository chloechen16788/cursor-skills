#!/usr/bin/env python3
"""把增量 CSV 里的文章抓下来。标题沿用 CSV，正文列保存 Firecrawl 的整段 markdown，再把这个文件发到固定群。"""

from __future__ import annotations

import csv
import os
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import cision_lib
import feishu_push

BODY_COLUMN = "正文"


def missing_firecrawl_message() -> str:
    return (
        "未设置 FIRECRAWL_API_KEY。请用户添加该密钥后再跑正文。"
        "已停止，未发送文件，也没有改当日表。"
    )


def firecrawl_key_present() -> bool:
    return bool(os.environ.get("FIRECRAWL_API_KEY", "").strip())


def gate_message() -> str | None:
    """密钥或命令缺失时返回错误文案。调用方不得发送文件，也不得访问当日表。"""
    if not firecrawl_key_present():
        return missing_firecrawl_message()
    if shutil.which("firecrawl") is None:
        return "找不到 firecrawl 命令。已停止，未发送文件，也没有改当日表。"
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


def after_from_delta_path(path: Path) -> str:
    head = path.parent.name.split("_", 1)[0]
    tail = head[9:15]
    if (
        len(head) != 16
        or head[8] != "T"
        or not head.endswith("Z")
        or not (head[:8] + tail).isdigit()
    ):
        raise RuntimeError("无法从增量路径得到窗口起点，请传入 --after。未发送文件")
    return f"{head[0:4]}-{head[4:6]}-{head[6:8]}T{head[9:11]}:{head[11:13]}:{head[13:15]}.000Z"


def shanghai_data_date(after: str) -> str:
    try:
        moment = datetime.strptime(after, "%Y-%m-%dT%H:%M:%S.000Z").replace(
            tzinfo=timezone.utc
        )
    except ValueError as error:
        raise RuntimeError(f"窗口起点无法解析，未发送文件：{after}") from error
    return moment.astimezone(cision_lib.SHANGHAI).date().isoformat()


def bodies_csv_path(delta_path: Path) -> Path:
    return delta_path.with_name(f"{delta_path.stem}-bodies.csv")


def build_record(item: dict, fetched: dict | None) -> dict:
    """标题只用 CSV。正文保存 Firecrawl markdown，不交给模型改写，也不截断。"""
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
    return record


def _data_rows(rows: list[list[str]]) -> list[list[str]]:
    return [row for row in rows if any(cell.strip() for cell in row)]


def _pad(row: list[str], width: int) -> list[str]:
    if len(row) >= width:
        return list(row[:width])
    return list(row) + [""] * (width - len(row))


def write_bodies_csv(
    path: Path, header: list[str], rows: list[list[str]], bodies: list[str]
) -> None:
    """在原增量列后追加正文。CSV 能放下超长换行文本；xlsx 单元格上限是 32767。"""
    if len(rows) != len(bodies):
        raise RuntimeError("正文行数和增量行数不一致，未发送文件")
    if BODY_COLUMN in header:
        raise RuntimeError("增量 CSV 已有正文列，未发送文件")
    cision_lib.ensure_output_dir(path.parent)
    path.parent.mkdir(parents=True, exist_ok=True)
    width = len(header)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow([*header, BODY_COLUMN])
        for row, body in zip(rows, bodies):
            writer.writerow([*_pad(row, width), body])


def read_bodies_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        return header, list(reader)


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


def run_bodies(
    *,
    header: list[str],
    rows: list[list[str]],
    after: str,
    scrape,
    send,
    dest: Path,
    secrets_ok: bool,
    secret_error: str = "",
) -> dict:
    data_rows = _data_rows(rows)
    if not data_rows:
        return {"bodies": "skipped", "delta_rows": 0, "feishu": "skipped"}
    if not secrets_ok:
        raise RuntimeError(secret_error or missing_firecrawl_message())
    if "url" not in header:
        raise RuntimeError("增量 CSV 缺少 url 列，未发送文件")
    data_date = shanghai_data_date(after)

    seen: set[str] = set()
    urls: list[str] = []
    for row in data_rows:
        url = _cell(header, row, "url")
        if url and url not in seen:
            seen.add(url)
            urls.append(url)
    try:
        fetched = scrape(urls) if urls else {}
    except Exception as error:  # noqa: BLE001
        detail = feishu_push.redact_secrets(str(error))
        raise RuntimeError(f"抓取没有完成，未发送文件，也没有改当日表：{detail}") from None
    if not isinstance(fetched, dict):
        raise RuntimeError("抓取结果不是按 url 索引的对象，未发送文件")

    bodies: list[str] = []
    scraped_ok = 0
    scraped_failed = 0
    stored_ok = 0
    for row in data_rows:
        item = {
            "id": _cell(header, row, "id"),
            "url": _cell(header, row, "url"),
            "csv_title": _cell(header, row, "title"),
        }
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
        bodies.append(record["正文"])

    try:
        write_bodies_csv(dest, header, data_rows, bodies)
    except Exception as error:  # noqa: BLE001
        raise RuntimeError(f"正文文件没有写成，未发送：{error}") from None
    try:
        send(dest)
    except Exception as error:  # noqa: BLE001
        raise RuntimeError(f"正文文件已写到 {dest}，群文件发送失败：{error}") from None
    return {
        "bodies": "written",
        "delta_rows": len(data_rows),
        "unique_urls": len(urls),
        "data_date": data_date,
        "scraped_ok": scraped_ok,
        "scraped_failed": scraped_failed,
        "stored_ok": stored_ok,
        "body_rows": len(data_rows),
        "body_csv": str(dest),
        "feishu": "sent",
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
            f"body_csv={summary['body_csv']}",
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
    dest = bodies_csv_path(delta_path)
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
            send=feishu_push.send_file,
            dest=dest,
            secrets_ok=blocked is None,
            secret_error=blocked or "",
        )
    finally:
        if owned:
            shutil.rmtree(directory, ignore_errors=True)
