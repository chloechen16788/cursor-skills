#!/usr/bin/env python3
"""把日报写入固定飞书文档，再生成 Word，把日期、链接和 Word 发到固定群。

先在内存里组好正文，再清空文档子块并重写。不删除 wiki 节点。
Word 由 baidu-competitor-daily/scripts/build_doc.py 生成，排序规则在那个脚本里。
群只走 feishu_push，不能改到别的会话。文本消息不含标题和正文。
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import OrderedDict, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import cision_lib
import feishu_push

REPORT_WIKI_TOKEN = "PP88weeBdi1Pcgkmpxbc48lSn5e"
REPORT_WIKI_URL = "https://prnewswire.feishu.cn/wiki/PP88weeBdi1Pcgkmpxbc48lSn5e"
SKILL_ROOT = Path(__file__).resolve().parent.parent / "baidu-competitor-daily"
DEFAULT_KB = SKILL_ROOT / "assets" / "翻译知识库.xlsx"
BUILD_DOC = SKILL_ROOT / "scripts" / "build_doc.py"
SECTION_TITLE = {
    "国内企业": "一、国内竞品（含领导人）",
    "自动驾驶": "二、自动驾驶竞品（含领导人）",
    "海外企业": "三、海外竞品（含领导人）",
    "企业领导人": "四、海外竞品领导人",
}
SECTIONS = ["国内企业", "自动驾驶", "海外企业", "企业领导人"]
SOURCE_TO_KB = {
    "Associated Press Online": "The Associated Press",
    "Bloomberg News Online": "Bloomberg",
}
COMPANY_CN = {
    "Microsoft": "微软",
    "Amazon": "亚马逊",
    "OpenAI": "OpenAI",
    "Anthropic": "Anthropic",
    "Alphabet/Google": "Alphabet/谷歌",
    "Google": "谷歌",
    "Apple": "苹果",
    "Nvidia": "英伟达",
    "IBM": "IBM",
    "Intel": "英特尔",
    "Meta": "Meta",
    "Tesla": "特斯拉",
}


def report_notice(data_date: str, counts: dict[str, int]) -> str:
    """群消息只有日期、四栏目条数和固定 wiki 链接。"""
    return "\n".join(
        [
            "百度海外舆情日报",
            f"data_date={data_date}",
            f"国内企业={counts['国内企业']}",
            f"自动驾驶={counts['自动驾驶']}",
            f"海外企业={counts['海外企业']}",
            f"企业领导人={counts['企业领导人']}",
            REPORT_WIKI_URL,
        ]
    )


def data_date_from_after(after: str) -> str:
    try:
        moment = datetime.strptime(after, "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=timezone.utc)
    except ValueError as error:
        raise RuntimeError(f"窗口起点无法解析，未改文档：{after}") from error
    return moment.astimezone(cision_lib.SHANGHAI).date().isoformat()


def _text_run(content: str, *, bold: bool = False, url: str = "") -> dict:
    style: dict = {}
    if bold:
        style["bold"] = True
    if url:
        style["link"] = {"url": quote(url, safe="")}
    element: dict = {"text_run": {"content": content}}
    if style:
        element["text_run"]["text_element_style"] = style
    return element


def _text_block(elements: list[dict]) -> dict:
    return {"block_type": 2, "text": {"elements": elements}}


def _heading(level: int, content: str) -> dict:
    key = {1: "heading1", 2: "heading2", 3: "heading3"}[level]
    block_type = {1: 3, 2: 4, 3: 5}[level]
    return {"block_type": block_type, key: {"elements": [_text_run(content)]}}


def _aliases_of(sec: str, ent: str) -> list[str]:
    if sec == "企业领导人":
        name = ent.split("(")[0].strip()
        return [name.lower()] if re.search(r"[A-Za-z]", name) else []
    outs = []
    for part in re.split(r"[/((（）)]", ent):
        part = part.strip()
        if part and re.search(r"[A-Za-z]", part):
            outs.append(part.lower())
    return outs


def load_zh(path: Path, final: list[dict]) -> dict[int, str]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    found: dict[int, str] = {}
    if isinstance(raw, list):
        for index, item in enumerate(raw):
            if isinstance(item, dict):
                found[int(item["idx"])] = str(item.get("zh") or "")
            else:
                found[index] = str(item)
    elif isinstance(raw, dict):
        for key, value in raw.items():
            found[int(key)] = value.get("zh", "") if isinstance(value, dict) else str(value)
    else:
        raise RuntimeError("zh.json 格式无法读取，未改文档")
    missing = [item["idx"] for item in final if not found.get(item["idx"], "").strip()]
    if missing or len(found) < len(final):
        raise RuntimeError(f"翻译条数与终稿不一致，未改文档：缺少 {len(missing)} 条")
    return {item["idx"]: found[item["idx"]] for item in final}


def prepare(final_path: Path, zh_path: Path, kb_path: Path) -> tuple[list[dict], dict[int, str], dict[str, str], dict[str, str]]:
    import openpyxl

    final = json.loads(final_path.read_text(encoding="utf-8"))
    if not isinstance(final, list):
        raise RuntimeError("final.json 不是列表，未改文档")
    zh = load_zh(zh_path, final)
    pairs = sorted({(item["section"], item["entity"]) for item in final})
    alias_index = []
    for sec, ent in pairs:
        for alias in _aliases_of(sec, ent):
            alias_index.append((alias, sec, ent))
    alias_index.sort(key=lambda item: -len(item[0]))

    def title_hits(title: str) -> list[tuple[int, str, str]]:
        hits = []
        lowered = title.lower()
        for alias, sec, ent in alias_index:
            match = re.search(r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])", lowered)
            if match:
                hits.append((match.start(), sec, ent))
        return hits

    for item in final:
        hits = title_hits(str(item.get("title") or ""))
        if not hits:
            continue
        if item["section"] in ("国内企业", "自动驾驶"):
            if any(sec in ("国内企业", "自动驾驶") for _, sec, _ in hits):
                continue
        leads = [hit for hit in hits if hit[1] == "企业领导人"]
        pick = min(leads or hits, key=lambda hit: hit[0])
        item["section"], item["entity"] = pick[1], pick[2]

    seen: set[str] = set()
    deduped = []
    for item in sorted(final, key=lambda row: row["idx"]):
        url = str(item.get("url") or "")
        if url in seen:
            continue
        seen.add(url)
        deduped.append(item)
    final = deduped

    workbook = openpyxl.load_workbook(kb_path, read_only=True)
    media_cn: dict[str, str] = {}
    for row in workbook["媒体名称知识库"].iter_rows(min_row=2, values_only=True):
        if row[0]:
            media_cn[str(row[0]).strip()] = str(row[1]).strip() if row[1] is not None else str(row[0]).strip()
    leader_cn: dict[str, str] = {}
    for row in workbook["领导人名称翻译知识库"].iter_rows(min_row=2, values_only=True):
        if row[0]:
            leader_cn[str(row[0]).strip()] = str(row[1]).strip() if row[1] is not None else str(row[0]).strip()
    leader_cn = {key: value for key, value in leader_cn.items() if value and value.lower() != key.lower()}
    for key, value in leader_cn.items():
        if " " not in key:
            continue
        for index, text in list(zh.items()):
            if key in text:
                zh[index] = text.replace(key, value)
    for index, text in list(zh.items()):
        zh[index] = re.sub(r"(?<=[\u4e00-\u9fff]) (?=[\u4e00-\u9fff])", "", text)
    return final, zh, media_cn, leader_cn


def _media_cn(source: str, media_cn: dict[str, str]) -> str:
    key = SOURCE_TO_KB.get(source.strip(), source.strip())
    if key in media_cn:
        return media_cn[key]
    if key.endswith(" Online") and key[:-7] in media_cn:
        return media_cn[key[:-7]]
    return media_cn.get(key, key)


def _leader_heading(ent: str, leader_cn: dict[str, str]) -> str:
    if " (" in ent:
        name, comp = ent.split(" (", 1)
        comp = comp.rstrip(")")
    else:
        name, comp = ent, ""
    chinese = leader_cn.get(name, name)
    comp_cn = COMPANY_CN.get(comp, comp)
    return f"{chinese}（{name}｜{comp_cn}）" if comp else f"{chinese}（{name}）"


# 品牌内排序与样例文档一致：先按标题把同一事件靠在一起，再把 Apple Intelligence
# （入华优先）整段抬到该品牌前面。没有 focus 的品牌，顺序仍按事件簇的最高影响力。
_EVENT_OVERLAP = 0.5
_EVENT_CAP = 0.55
_EV_GROUP_STOP = {
    "the", "and", "for", "with", "that", "this", "from", "are", "was", "were", "has", "have",
    "will", "its", "his", "her", "not", "but", "you", "can", "how", "why", "what", "who", "out",
    "new", "more", "says", "said", "into", "over", "after", "amid", "about", "than", "then",
    "they", "their", "inc", "nasdaq", "nyse", "stock", "stocks", "shares", "report", "reports",
    "now", "just", "still", "first", "could", "would", "may", "might", "one", "two", "three",
    "is", "be", "to", "of", "in", "on", "at", "as", "by", "or", "an", "a",
}
_FOCUS_RANK = {"apple_intel_cn": 0, "apple_intel": 1}
_FOCUS_NORMAL = 2


def _ev_tokens(title: str) -> set[str]:
    return {
        word
        for word in re.findall(r"[a-z0-9]+", title.lower())
        if len(word) >= 3 and word not in _EV_GROUP_STOP
    }


def _discover_events(items: list[dict]) -> list[list[dict]]:
    """同一品牌下，措辞不同但讲同一件事的标题排在一起。"""
    count = len(items)
    if count <= 1:
        return [list(items)] if items else []
    by_word: dict[str, set[int]] = defaultdict(set)
    for index, item in enumerate(items):
        for word in _ev_tokens(str(item.get("title") or "")):
            by_word[word].add(index)
    upper = max(2, int(count * 0.8))
    cap = max(3, int(count * _EVENT_CAP))
    candidates = {word: hits for word, hits in by_word.items() if 2 <= len(hits) <= upper}
    clusters: list[dict[str, set[int]]] = []
    for word in sorted(candidates, key=lambda item: (-len(candidates[item]), item)):
        titles = candidates[word]
        target = None
        for cluster in clusters:
            overlap = len(titles & cluster["titles"])
            if overlap and overlap / min(len(titles), len(cluster["titles"])) >= _EVENT_OVERLAP:
                if len(cluster["titles"] | titles) <= cap:
                    target = cluster
                    break
        if target is not None:
            target["titles"] |= titles
            continue
        absorbed = False
        for cluster in clusters:
            overlap = len(titles & cluster["titles"])
            if overlap and overlap / min(len(titles), len(cluster["titles"])) >= _EVENT_OVERLAP:
                absorbed = True
                break
        if not absorbed:
            clusters.append({"titles": set(titles)})
    assigned: set[int] = set()
    grouped: list[list[dict]] = []
    for cluster in sorted(clusters, key=lambda item: -len(item["titles"])):
        fresh = cluster["titles"] - assigned
        if len(fresh) >= 2:
            grouped.append([items[index] for index in sorted(fresh)])
            assigned |= fresh
    for index in range(count):
        if index not in assigned:
            grouped.append([items[index]])

    def focus_rank(cluster: list[dict]) -> int:
        return min(_FOCUS_RANK.get(str(item.get("focus") or ""), _FOCUS_NORMAL) for item in cluster)

    grouped.sort(key=lambda cluster: (focus_rank(cluster), -max(item["impact"] for item in cluster)))
    for cluster in grouped:
        cluster.sort(key=lambda item: (_FOCUS_RANK.get(str(item.get("focus") or ""), _FOCUS_NORMAL), -item["impact"]))
    return grouped


def _ordered_items(items: list[dict]) -> list[dict]:
    """先聚事件，再按 focus 稳定分块，入华在前。"""
    base: list[dict] = []
    for cluster in _discover_events(items):
        base.extend(cluster)
    blocks: OrderedDict[str, list[dict]] = OrderedDict()
    for item in base:
        blocks.setdefault(str(item.get("focus") or ""), []).append(item)
    ordered: list[dict] = []
    for key in sorted(blocks, key=lambda name: _FOCUS_RANK.get(name, _FOCUS_NORMAL)):
        ordered.extend(blocks[key])
    return ordered


def build_blocks(
    final: list[dict],
    zh: dict[int, str],
    media_cn: dict[str, str],
    leader_cn: dict[str, str],
    *,
    data_date: str,
    raw_count: int,
) -> tuple[list[dict], dict[str, int]]:
    del data_date  # 日期只出现在群消息里，样例文档正文不写数据日期
    missing = sorted({item["media_kb"] for item in final if item.get("media_kb") not in media_cn})
    if missing:
        raise RuntimeError("终稿媒体不在翻译知识库中，未改文档：" + ", ".join(missing))
    groups: OrderedDict[str, dict[str, list[dict]]] = OrderedDict((sec, defaultdict(list)) for sec in SECTIONS)
    for item in final:
        groups[item["section"]][item["entity"]].append(item)
    raw_label = str(raw_count) if raw_count else "—"
    blocks = [
        _text_block([
            _text_run(f"原始记录 {raw_label} 条，筛选入报告 {len(final)} 条（同一报道仅归入一个板块）")
        ]),
        _text_block([
            _text_run("筛选说明：", bold=True),
            _text_run(
                "仅保留重点市场（中国、美国、英国、中东等）报道，且本期仅收录英文稿件；媒体来源限定于《翻译知识库》「媒体名称知识库」所列媒体，其余来源不收录。"
                "已剔除 Windows/安卓补丁、手机/电脑硬件、医药/音箱、纯电商物流、非重点市场（法/意/德/日/新等）、低价值通稿与分析师评级类内容；"
                "亦剔除加密货币、财报前瞻（实际业绩保留）、纯股价波动快讯，以及星链/SpaceX/推特、电动车换代、外卖等非重点话题。"
            ),
        ]),
    ]
    counts = {sec: 0 for sec in SECTIONS}
    for sec in SECTIONS:
        if not groups[sec]:
            continue
        blocks.append(_heading(1, SECTION_TITLE[sec]))
        entities = sorted(groups[sec].items(), key=lambda pair: -max(item["impact"] for item in pair[1]))
        for ent, items in entities:
            heading = _leader_heading(ent, leader_cn) if sec == "企业领导人" else ent
            blocks.append(_heading(2, heading))
            for item in _ordered_items(items):
                media = str(item["media_kb"])
                title = str(item["title"]).strip()
                blocks.append(_text_block([
                    _text_run(f"{media}: {title}", bold=True, url=str(item["url"])),
                ]))
                blocks.append(_text_block([
                    _text_run(_media_cn(media, media_cn) + "：" + zh[item["idx"]], bold=True),
                ]))
                counts[sec] += 1
    return blocks, counts


def _api(token: str, method: str, url: str, payload: dict | None = None) -> dict:
    return feishu_push.api_request(url, method, payload, token=token)


def resolve_doc(token: str) -> str:
    body = _api(
        token,
        "GET",
        f"https://open.feishu.cn/open-apis/wiki/v2/spaces/get_node?token={REPORT_WIKI_TOKEN}",
    )
    node = (body.get("data") or {}).get("node") or {}
    if str(node.get("node_token") or "") not in ("", REPORT_WIKI_TOKEN):
        raise RuntimeError("wiki 节点 token 不符，未改文档")
    if str(node.get("obj_type") or "") != "docx" or not node.get("obj_token"):
        raise RuntimeError(f"wiki 节点不是可写的 docx，未改文档：obj_type={node.get('obj_type') or 'empty'}")
    return str(node["obj_token"])


def list_children(token: str, doc_id: str) -> list[dict]:
    items: list[dict] = []
    page_token = ""
    for _ in range(50):
        query = "page_size=500"
        if page_token:
            query += "&page_token=" + quote(page_token, safe="")
        data = _api(
            token,
            "GET",
            f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children?{query}",
        ).get("data") or {}
        items.extend(data.get("items") or [])
        if not data.get("has_more"):
            return items
        page_token = str(data.get("page_token") or "")
        if not page_token:
            return items
    raise RuntimeError("文档子块分页超过预期，已停止")


def clear_body(token: str, doc_id: str) -> int:
    removed = 0
    for _ in range(100):
        children = list_children(token, doc_id)
        if not children:
            return removed
        end = min(len(children), 500)
        _api(
            token,
            "DELETE",
            f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children/batch_delete",
            {"start_index": 0, "end_index": end},
        )
        removed += end
    raise RuntimeError("清空文档正文未完成")


def write_blocks(token: str, doc_id: str, blocks: list[dict]) -> int:
    written = 0
    for start in range(0, len(blocks), 50):
        chunk = blocks[start : start + 50]
        _api(
            token,
            "POST",
            f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children",
            {"children": chunk, "index": -1},
        )
        written += len(chunk)
    return written


def write_word(final_path: Path, zh_path: Path, kb_path: Path, *, data_date: str, raw_count: int) -> Path:
    """用第五版 build_doc.py 生成 Word。失败时还没发群消息。"""
    if not BUILD_DOC.is_file():
        raise RuntimeError(f"找不到 build_doc.py，未发群消息：{BUILD_DOC}")
    out = final_path.resolve().parent / f"百度海外舆情日报_竞品与领导人_{data_date}.docx"
    completed = subprocess.run(
        [
            sys.executable,
            str(BUILD_DOC),
            "--final",
            str(final_path),
            "--zh",
            str(zh_path),
            "--kb",
            str(kb_path),
            "--raw-count",
            str(raw_count),
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0 or not out.is_file():
        detail = (completed.stderr or completed.stdout or "无输出").strip()
        raise RuntimeError(f"文档已重写，Word 未生成，未发群消息：{detail}")
    return out


def publish(*, final_path: Path, zh_path: Path, kb_path: Path, after: str, raw_count: int, send) -> dict:
    data_date = data_date_from_after(after)
    final, zh, media_cn, leader_cn = prepare(final_path, zh_path, kb_path)
    blocks, counts = build_blocks(
        final, zh, media_cn, leader_cn, data_date=data_date, raw_count=raw_count
    )
    if not feishu_push.credentials_present():
        raise RuntimeError(feishu_push.missing_credentials_message())
    token = feishu_push.tenant_token()
    doc_id = resolve_doc(token)
    cleared = clear_body(token, doc_id)
    if list_children(token, doc_id):
        raise RuntimeError("清空后仍有子块，未写入新正文，也未发群消息")
    written = write_blocks(token, doc_id, blocks)
    if len(list_children(token, doc_id)) != written:
        raise RuntimeError("写入后的子块数与预期不符，未发群消息")
    docx_path = write_word(
        final_path, zh_path, kb_path, data_date=data_date, raw_count=raw_count
    )
    notice = report_notice(data_date, counts)
    try:
        send(notice)
    except Exception as error:  # noqa: BLE001
        detail = feishu_push.redact_secrets(str(error))
        raise RuntimeError(f"文档已重写，群消息发送失败：{detail}") from None
    try:
        feishu_push.send_file(docx_path)
    except Exception as error:  # noqa: BLE001
        detail = feishu_push.redact_secrets(str(error))
        raise RuntimeError(f"文档已重写，说明已发送，Word 发送失败：{detail}") from None
    return {
        "data_date": data_date,
        "cleared_children": cleared,
        "written_blocks": written,
        "counts": counts,
        "wiki_url": REPORT_WIKI_URL,
        "docx": str(docx_path),
        "feishu": "sent",
    }


def format_summary(summary: dict) -> str:
    counts = summary["counts"]
    return "\n".join(
        [
            f"data_date={summary['data_date']}",
            f"国内企业={counts['国内企业']}",
            f"自动驾驶={counts['自动驾驶']}",
            f"海外企业={counts['海外企业']}",
            f"企业领导人={counts['企业领导人']}",
            f"cleared_children={summary['cleared_children']}",
            f"written_blocks={summary['written_blocks']}",
            f"wiki_url={summary['wiki_url']}",
            f"docx={summary['docx']}",
            f"feishu={summary['feishu']}",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="清空并重写固定飞书日报文档，生成 Word，再把日期、链接和 Word 发到固定群")
    parser.add_argument("--final", required=True, help="prep_final.py 写出的 final.json")
    parser.add_argument("--zh", required=True, help="按 idx 填好的 zh.json")
    parser.add_argument("--kb", default=str(DEFAULT_KB), help="翻译知识库.xlsx，默认用技能里的那份")
    parser.add_argument("--after", required=True, help="导出摘要里的 after，用来算上海数据日期")
    parser.add_argument("--raw-count", type=int, default=0, help="进入筛选的原始行数，只写在文档副标题")
    args = parser.parse_args()
    summary = publish(
        final_path=Path(args.final),
        zh_path=Path(args.zh),
        kb_path=Path(args.kb),
        after=args.after,
        raw_count=args.raw_count,
        send=feishu_push.send_text,
    )
    print(format_summary(summary))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # noqa: BLE001
        print(feishu_push.redact_secrets(str(error)), file=sys.stderr)
        sys.exit(1)
