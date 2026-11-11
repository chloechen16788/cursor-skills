#!/usr/bin/env python3
"""build_doc.py — 百度竞品同业日报 · 第四步：生成 Word。

读取 final.json + zh.json（人工翻译，按 idx 对齐）+ 翻译知识库（媒体/领导人标准译名），
生成两行式带超链接的 Word 报告。

格式（每条两行）：
  英文媒体: 英文标题        ← 半角冒号；媒体名与标题各自带超链接（同指向原文）
  中文媒体：中文标题
"""

import argparse
import json
import re
import openpyxl
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from collections import defaultdict, OrderedDict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--final", required=True)
    ap.add_argument(
        "--zh", required=True, help="翻译文件（zh.json，按 idx 对齐的列表或含 zh 字段）"
    )
    ap.add_argument("--kb", required=True, help="翻译知识库.xlsx")
    ap.add_argument("--title", default="百度海外舆情日报 · 竞品与领导人")
    ap.add_argument(
        "--raw-count", type=int, default=0, help="原始记录总数（仅用于副标题，可选）"
    )
    ap.add_argument("--out", default="百度海外舆情日报_竞品与领导人.docx")
    args = ap.parse_args()

    final = json.load(open(args.final))
    # 定时流水线的 section 字段仍是发布脚本用的四个名字。Word 展示沿用第五版的三个竞品标题。
    for item in final:
        item["section"] = {
            "国内企业": "国内竞品",
            "自动驾驶": "自动驾驶竞品",
            "海外企业": "海外竞品",
        }.get(item["section"], item["section"])

    # 读取翻译：支持 [ {idx, zh}, ... ] 或 [ "中文", ... ] 两种格式
    zh_raw = json.load(open(args.zh))
    ZH = {}
    if isinstance(zh_raw, list):
        for i, item in enumerate(zh_raw):
            if isinstance(item, dict):
                ZH[item["idx"]] = item.get("zh", "")
            else:
                ZH[i] = item
    elif isinstance(zh_raw, dict):
        for k, v in zh_raw.items():
            ZH[int(k)] = v.get("zh", "") if isinstance(v, dict) else v
    # 按 final 顺序展开
    ZH = [ZH.get(x["idx"], "") for x in final]
    assert len(ZH) == len(final), f"ZH {len(ZH)} vs final {len(final)}"

    # ---- 1) 归属唯一化（与 prep_final 一致） ----
    pairs = sorted(set((x["section"], x["entity"]) for x in final))

    def aliases_of(sec, ent):
        # 三板块口径下已无「企业领导人」板块：领导人稿件挂在其品牌下，
        # 这里只需处理仍以领导人实体存在的少数情况（实体名带括号）。
        if "(" in ent or "（" in ent:
            name = re.split(r"[(（]", ent)[0].strip()
            return [name.lower()] if re.search(r"[A-Za-z]", name) else []
        if ent == "Cruise":
            return []  # 避免 "Tom Cruise" 等被误归并到 Cruise
        outs = []
        for p in re.split(r"[/((（）)]", ent):
            p = p.strip()
            if p and re.search(r"[A-Za-z]", p):
                outs.append(p.lower())
        return outs

    alias_index = []
    for sec, ent in pairs:
        for a in aliases_of(sec, ent):
            alias_index.append((a, sec, ent))
    alias_index.sort(key=lambda t: -len(t[0]))

    def title_hits(tl):
        hits = []
        for a, sec, ent in alias_index:
            m = re.search(r"(?<![a-z0-9])" + re.escape(a) + r"(?![a-z0-9])", tl)
            if m:
                hits.append((m.start(), sec, ent))
        return hits

    for x in final:
        hits = title_hits(x["title"].lower())
        if not hits:
            continue
        if x["section"] in ("国内竞品", "自动驾驶竞品"):
            if any(s in ("国内竞品", "自动驾驶竞品") for _, s, _ in hits):
                continue
        pick = min(hits, key=lambda h: (h[0], h[1], h[2]))
        x["section"], x["entity"] = pick[1], pick[2]

    # 2) URL 去重
    seen_urls = set()
    _deduped = []
    for x in sorted(final, key=lambda i: i["idx"]):
        if x["url"] in seen_urls:
            continue
        seen_urls.add(x["url"])
        _deduped.append(x)
    final = _deduped

    # ---- 知识库：媒体标准译名 & 领导人标准译名 ----
    kb_wb = openpyxl.load_workbook(args.kb)
    MEDIA_CN = {}
    for _r in kb_wb["媒体名称知识库"].iter_rows(min_row=2, values_only=True):
        if _r[0]:
            MEDIA_CN[str(_r[0]).strip()] = (
                str(_r[1]).strip() if _r[1] is not None else str(_r[0]).strip()
            )
    LEADER_CN = {}
    for _r in kb_wb["领导人名称翻译知识库"].iter_rows(min_row=2, values_only=True):
        if _r[0]:
            LEADER_CN[str(_r[0]).strip()] = (
                str(_r[1]).strip() if _r[1] is not None else str(_r[0]).strip()
            )
    LEADER_CN = {k: v for k, v in LEADER_CN.items() if v and v.lower() != k.lower()}

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

    def leader_heading(ent):
        if " (" in ent:
            name, comp = ent.split(" (", 1)
            comp = comp.rstrip(")")
        else:
            name, comp = ent, ""
        cn = LEADER_CN.get(name, name)
        comp_cn = COMPANY_CN.get(comp, comp)
        return f"{cn}（{name}｜{comp_cn}）" if comp else f"{cn}（{name}）"

    # 中文标题里的英文领导人全名 -> 标准中文（仅替换含空格全名，避免短名误伤）
    for _k, _v in LEADER_CN.items():
        if " " in _k:
            for _i in range(len(ZH)):
                if _k in ZH[_i]:
                    ZH[_i] = ZH[_i].replace(_k, _v)
    for _i in range(len(ZH)):
        ZH[_i] = re.sub(r"(?<=[\u4e00-\u9fff]) (?=[\u4e00-\u9fff])", "", ZH[_i])

    SOURCE_TO_KB = {
        "Associated Press Online": "The Associated Press",
        "Bloomberg News Online": "Bloomberg",
    }

    def media_cn_of(src):
        s = src.strip()
        key = SOURCE_TO_KB.get(s, s)
        if key in MEDIA_CN:
            return MEDIA_CN[key]
        if key.endswith(" Online") and key[:-7] in MEDIA_CN:
            return MEDIA_CN[key[:-7]]
        return MEDIA_CN.get(key, key)

    SECTION_TITLE = {
        "国内竞品": "一、国内竞品（含领导人）",
        "自动驾驶竞品": "二、自动驾驶竞品（含领导人）",
        "海外竞品": "三、海外竞品（含领导人）",
    }
    show_sections = ["国内竞品", "自动驾驶竞品", "海外竞品"]
    if any(item["section"] == "企业领导人" for item in final):
        show_sections.append("企业领导人")
        SECTION_TITLE["企业领导人"] = "四、海外竞品领导人"

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10.5)
    style.element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")

    ttl = doc.add_heading(args.title, level=0)
    for _r in ttl.runs:
        _r.bold = True
    sub = doc.add_paragraph()
    cnt = len(final)
    r = sub.add_run(
        f"原始记录 {args.raw_count or '—'} 条，筛选入报告 {cnt} 条（同一报道仅归入一个板块）"
    )
    r.font.size = Pt(9)
    r.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

    note = doc.add_paragraph()
    nr = note.add_run("筛选说明：")
    nr.bold = True
    note.add_run(
        "仅保留重点市场（中国、美国、英国、中东等）报道，且本期仅收录英文稿件；媒体来源限定于《翻译知识库》「媒体名称知识库」所列媒体，其余来源不收录。"
        "已剔除 Windows/安卓补丁、手机/电脑硬件、医药/音箱、纯电商物流、非重点市场（法/意/德/日/新等）、低价值通稿与分析师评级类内容；"
        "亦剔除加密货币、财报前瞻（实际业绩保留）、纯股价波动快讯，以及星链/SpaceX/推特、电动车换代、外卖等非重点话题。"
        "同事件多媒体报道已就近归并；相同品牌内容归集于该品牌下；同一报道仅归入一个板块。标题中文译法为人工校对，供参考。"
    )
    note.runs[-1].font.size = Pt(9)
    note.runs[-1].font.color.rgb = RGBColor(0x66, 0x66, 0x66)

    def norm_title(t):
        return re.sub(r"[^a-z0-9]+", "", t.lower())

    # ===== 事件分组：从标题自动发现，不依赖任何主题词表 =====
    # 早期版本用手写标签（school_ai / mna / buyout…），每换一批数据就失效。改为纯数据驱动。
    #
    # 算法（词级单链合并 + 规模护栏）：
    #   1) 词 → 包含它的标题集合。只出现在 1 条的词无共现证据；出现在 ≥80% 标题的词
    #      （品牌名等）无区分度 —— 两者都排除。
    #   2) 按标题集合从大到小处理词：若某词与已有簇的标题集合重合度
    #      ≥ EVENT_OVERLAP（用 min 归一，容忍长短标题不对称），并入该簇。
    #   3) **护栏**：合并后簇覆盖的标题数不得超过 EVENT_CAP×该实体总数。
    #      没有这道护栏，大品牌会因链式传递塌缩成一个巨簇
    #      （实测旧批次 Apple 46 条曾被并成 45 条一簇）。
    #   4) 剩余未覆盖的标题各自独立成簇。
    #   5) 所有簇按簇内最高 impact 降序，簇内按 impact 降序。
    #
    # 阈值依据（在新旧两批数据上回归）：
    #   EVENT_OVERLAP=0.5：新批次 Google 学校政策 12 篇、马来西亚投资 8 篇、离职补偿 3 篇，
    #   Uber 财报 10 篇、Robotaxi 3 篇均完整成簇；0.6 起大簇开始碎裂。
    #   EVENT_CAP=0.55：旧批次 Apple 46 条分成 [21,10,7,3]，既不成巨簇也不过度碎片化。
    EVENT_OVERLAP = 0.5
    EVENT_CAP = 0.55

    EV_GROUP_STOP = {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "from",
        "are",
        "was",
        "were",
        "has",
        "have",
        "will",
        "its",
        "his",
        "her",
        "not",
        "but",
        "you",
        "can",
        "how",
        "why",
        "what",
        "who",
        "out",
        "new",
        "more",
        "says",
        "said",
        "into",
        "over",
        "after",
        "amid",
        "about",
        "than",
        "then",
        "they",
        "their",
        "inc",
        "nasdaq",
        "nyse",
        "stock",
        "stocks",
        "shares",
        "report",
        "reports",
        "now",
        "just",
        "still",
        "first",
        "could",
        "would",
        "may",
        "might",
        "one",
        "two",
        "three",
        "is",
        "are",
        "be",
        "to",
        "of",
        "in",
        "on",
        "at",
        "as",
        "by",
        "or",
        "an",
        "a",
    }

    def _ev_tokens(t):
        return {
            w
            for w in re.findall(r"[a-z0-9]+", t.lower())
            if len(w) >= 3 and w not in EV_GROUP_STOP
        }

    # 重点关注排序权重：数值越小越靠前。
    # apple_intel_cn（Apple Intelligence·入华）最前，其次 apple_intel，其余保持原 impact 排序。
    FOCUS_RANK = {"apple_intel_cn": 0, "apple_intel": 1}
    FOCUS_NORMAL = 2

    def discover_events(items):
        """把同一实体下的标题自动聚成事件簇，返回 [[item, ...], ...]。"""
        n = len(items)
        if n <= 1:
            return [list(items)] if items else []

        by_word = defaultdict(set)
        for i, x in enumerate(items):
            for w in _ev_tokens(x["title"]):
                by_word[w].add(i)

        upper = max(2, int(n * 0.8))  # 超过 80% 标题的词 → 品牌名等，无区分度
        cap = max(3, int(n * EVENT_CAP))  # 单簇规模上限，防链式塌缩
        cand = {w: s for w, s in by_word.items() if 2 <= len(s) <= upper}

        clusters = []
        for w in sorted(cand, key=lambda w: (-len(cand[w]), w)):
            s = cand[w]
            target = None
            for c in clusters:
                inter = len(s & c["titles"])
                if inter and inter / min(len(s), len(c["titles"])) >= EVENT_OVERLAP:
                    if len(c["titles"] | s) <= cap:
                        target = c
                        break
            if target is not None:
                target["titles"] |= s
            else:
                # 已达上限：不再扩标题，但记为该簇的归属词（避免另起重复簇）
                absorbed = False
                for c in clusters:
                    inter = len(s & c["titles"])
                    if inter and inter / min(len(s), len(c["titles"])) >= EVENT_OVERLAP:
                        absorbed = True
                        break
                if not absorbed:
                    clusters.append({"titles": set(s)})

        assigned = set()
        out = []
        for c in sorted(clusters, key=lambda c: -len(c["titles"])):
            g = c["titles"] - assigned
            if len(g) >= 2:
                out.append([items[i] for i in sorted(g)])
                assigned |= g
        for i in range(n):
            if i not in assigned:
                out.append([items[i]])

        # 客户重点关注（focus）优先，其余完全沿用原口径「按簇内最高 impact 降序」。
        # 不要在此引入 pscore 作为排序键：pscore 只在 prep_final 的同实体同标题分组内生效，
        # 放到这里会连带改动其它品牌的既有顺序（实测会让 Nvidia 等板块重排 17 处）。
        def _focus_rank(cluster):
            return min(
                FOCUS_RANK.get(i.get("focus", ""), FOCUS_NORMAL) for i in cluster
            )

        out.sort(key=lambda c: (_focus_rank(c), -max(i["impact"] for i in c)))
        for c in out:
            c.sort(
                key=lambda i: (
                    FOCUS_RANK.get(i.get("focus", ""), FOCUS_NORMAL),
                    -i["impact"],
                )
            )
        return out

    def group_by_topic(items):
        """同一实体下同事件的报道相邻输出（事件由标题自动发现，见 discover_events）。

        客户重点关注的稿件（focus：Apple Intelligence，尤其入华）整体提到板块最前。

        实现要点：**先用全量 items 做一次事件聚类**得到基础顺序，再按 focus 做**稳定分块**
        （块内保持基础顺序的相对次序）。
        - 不能直接对「分块后的子集」聚类：样本数变化会改变 df/阈值，连带挪动其它品牌的顺序
          （实测让 Nvidia、Intel 等板块出现 17 处位移）。
        - 本做法下，没有 focus 的实体分块结果与原顺序完全一致，零副作用。
        """
        base = []
        for c in discover_events(items):
            base.extend(c)

        blocks = OrderedDict()
        for it in base:
            blocks.setdefault(it.get("focus", "") or "", []).append(it)

        out = []
        for key in sorted(blocks, key=lambda k: FOCUS_RANK.get(k, FOCUS_NORMAL)):
            out.extend(blocks[key])
        return out

    groups = OrderedDict()
    for sec in show_sections:
        groups[sec] = defaultdict(list)
    for x in final:
        groups[x["section"]][x["entity"]].append(x)

    LINK_COLOR = "0563C1"

    def _xml_run(text, bold=False, link=False):
        run = OxmlElement("w:r")
        rPr = OxmlElement("w:rPr")
        if bold:
            rPr.append(OxmlElement("w:b"))
        if link:
            color = OxmlElement("w:color")
            color.set(qn("w:val"), LINK_COLOR)
            u = OxmlElement("w:u")
            u.set(qn("w:val"), "single")
            rPr.append(color)
            rPr.append(u)
        run.append(rPr)
        t = OxmlElement("w:t")
        t.text = text
        t.set(qn("xml:space"), "preserve")
        run.append(t)
        return run

    def add_link(paragraph, url, text, bold=False):
        """在段落末尾追加一个超链接片段（媒体名与标题各自调用，都指向原文）。"""
        r_id = doc.part.relate_to(url, RT.HYPERLINK, is_external=True)
        hyperlink = OxmlElement("w:hyperlink")
        hyperlink.set(qn("r:id"), r_id)
        hyperlink.append(_xml_run(text, bold=bold, link=True))
        paragraph._p.append(hyperlink)
        return paragraph

    entry_count = 0
    for sec in show_sections:
        doc.add_heading(SECTION_TITLE[sec], level=1)
        ent_dict = groups[sec]
        ents = sorted(ent_dict.items(), key=lambda kv: -max(i["impact"] for i in kv[1]))
        for ent, items in ents:
            # 品牌直接用实体名；仍以领导人实体单列的少数情况保留「中文名（英文名｜公司）」格式
            h2_text = leader_heading(ent) if sec not in SECTION_TITLE else ent
            if h2_text == ent and (" (" in ent):
                h2_text = leader_heading(ent)
            doc.add_heading(h2_text, level=2)
            for it in group_by_topic(items):
                zh = ZH[it["idx"]]
                media_en_disp = it["media_kb"]
                media_cn = MEDIA_CN.get(media_en_disp, media_en_disp)
                p1 = doc.add_paragraph()
                p1.paragraph_format.left_indent = Inches(0.2)
                # 英文媒体名 + 冒号 + 英文标题，三段均为超链接、同指向原文，全部加粗
                add_link(p1, it["url"], media_en_disp, bold=True)
                add_link(p1, it["url"], ": ", bold=True)
                add_link(p1, it["url"], it["title"].strip(), bold=True)
                p2 = doc.add_paragraph()
                p2.paragraph_format.left_indent = Inches(0.2)
                p2.paragraph_format.space_after = Pt(6)
                # 中文行：媒体名 + 全角冒号 + 中文标题，全部加粗
                r2 = p2.add_run(media_cn + "：")
                r2.font.size = Pt(10.5)
                r2.bold = True
                rz = p2.add_run(zh)
                rz.font.size = Pt(10.5)
                rz.bold = True
                entry_count += 1

    doc.save(args.out)
    print("Saved:", args.out, "| entries:", entry_count)


if __name__ == "__main__":
    main()
