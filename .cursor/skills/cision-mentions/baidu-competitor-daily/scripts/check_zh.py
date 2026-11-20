#!/usr/bin/env python3
"""check_zh.py — 百度竞品同业日报 · 译文规范校验。

在 build_doc 之前跑一遍，拦住两类**必然会被客户指出来**的译文问题：

1. **`AI` 不翻译**。中文标题里出现「人工智能」一律报错，应改为 `AI`
   （`AI agent` → `AI 智能体`、`AI chip` → `AI 芯片`）。`AGI` / `LLM` / `GPU` 同理保留原文。
2. **品牌名必须用《翻译知识库》的中文名**。中文标题里残留英文品牌名（`Z.AI`、`Zhipu`、`Google`、
   `Huawei`…）一律报错。特别注意 `Z.AI`：它是**公司名**，要译成「智谱」；
   而同一句里的 `GLM-5`、`ChatGLM` 是产品名，保留原文——所谓「AI 不翻译」指的是通用词，
   不是把公司名里的 AI 也留着。

用法：
    python check_zh.py --zh zh.json --template zh_template.json --kb 翻译知识库.xlsx
    # 仅告警不拦截（用于历史稿件复核）：--soft

退出码：0 = 通过；1 = 存在 error。
"""
import argparse
import json
import re
import sys

import openpyxl

# 中文标题里不应出现的译法 → 建议写法
BANNED_TERMS = {
    '人工智能': 'AI',
    '人工智慧': 'AI',
    '生成式人工智能': '生成式 AI',
}

# 允许保留英文的品牌（KB 中文名本身就是英文）
IDS = re.compile(r'[A-Za-z0-9.\-]')

# 品类词：不是公司，不该按品牌名要求翻译（报告里一贯沿用 Robotaxi）
SKIP_ALIASES = {'robotaxi', 'robotaxis', 'cybercab', 'cruise', 'fsd', 'adas'}

# 产品名/固定搭配：整段保留英文，做品牌检查前先抹掉，避免 "Apple" 命中 "Apple Intelligence"
PRODUCT_PHRASES = [
    'apple intelligence', 'apple tv', 'apple music', 'apple pay', 'apple card',
    'apple watch', 'apple vision', 'apple arcade', 'apple news', 'apple maps',
    'apple silicon', 'apple id',
]


def mask_products(text):
    low = text.lower()
    out = list(text)
    for ph in PRODUCT_PHRASES:
        start = 0
        while True:
            i = low.find(ph, start)
            if i < 0:
                break
            for k in range(i, i + len(ph)):
                out[k] = '·'
            start = i + len(ph)
    return ''.join(out)


def load_brand_map(kb_path):
    """KB 品牌表 → [(英文写法, 中文名)]，只保留中英不同的条目。"""
    wb = openpyxl.load_workbook(kb_path)
    ws = wb['品牌名称翻译知识库']
    out = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        en = (row[0] or '').strip()
        cn = (row[1] or '').strip()
        if not en or not cn:
            continue
        for part in [p.strip() for p in en.split('/') if p.strip()]:
            if part.lower() == cn.lower():
                continue          # 中文名就是英文原文（OpenAI / Anthropic / IBM …）
            if not re.search(r'[\u4e00-\u9fff]', cn):
                continue          # 中文列仍是纯英文（ChatGPT / Claude / Gemini），无需替换
            if part.lower() in SKIP_ALIASES:
                continue          # 品类词（Robotaxi），报告一贯保留英文
            if len(part) < 3:
                continue          # 过短的写法容易误伤
            out.append((part, cn))
    # 长写法优先，避免 "Google DeepMind" 被 "Google" 先吃掉
    out.sort(key=lambda t: -len(t[0]))
    return out


def build_pattern(alias):
    """完整词匹配；含点号时不能用 \\b，用前后非字母数字边界。"""
    esc = re.escape(alias)
    return re.compile(r'(?<![A-Za-z0-9])' + esc + r'(?![A-Za-z0-9])')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--zh', required=True)
    ap.add_argument('--template', required=True)
    ap.add_argument('--kb', required=True)
    ap.add_argument('--soft', action='store_true', help='只报告，不以非零码退出')
    args = ap.parse_args()

    zh_raw = json.load(open(args.zh))
    if isinstance(zh_raw, list):
        ZH = {x['idx']: x.get('zh', '') for x in zh_raw}
    else:
        ZH = {int(k): v for k, v in zh_raw.items()}

    tpl = json.load(open(args.template))
    brand_map = [(a, cn, build_pattern(a)) for a, cn in load_brand_map(args.kb)]

    errors, warns = [], []
    for item in tpl:
        idx, en, txt = item['idx'], item['en'], ZH.get(item['idx'], '')
        if not txt:
            errors.append((idx, '缺译', en[:70]))
            continue
        for bad, good in BANNED_TERMS.items():
            if bad in txt:
                errors.append((idx, f'「{bad}」应写作「{good}」', txt[:80]))
        masked = mask_products(txt)
        for alias, cn, pat in brand_map:
            if pat.search(masked):
                errors.append((idx, f'品牌英文名「{alias}」应译为「{cn}」', txt[:80]))
        # AI 与中文之间的空格（团队既有排版习惯：AI 智能体）
        # 前置非字母边界：避免把 OpenAI/Anthropic 里的 AI 当成独立词报出来
        for m in re.finditer(r'(?<![A-Za-z])AI(?=[\u4e00-\u9fff])', txt):
            warns.append((idx, 'AI 后缺空格', txt[max(0, m.start() - 12):m.start() + 12]))

    print(f'检查 {len(tpl)} 条；error {len(errors)}，warning {len(warns)}')
    for idx, why, ctx in errors[:40]:
        print(f'  [E{idx:>3}] {why}  ← {ctx}')
    if len(errors) > 40:
        print(f'  …另有 {len(errors) - 40} 条 error')
    for idx, why, ctx in warns[:10]:
        print(f'  [W{idx:>3}] {why}  ← {ctx}')

    if errors and not args.soft:
        sys.exit(1)


if __name__ == '__main__':
    main()
