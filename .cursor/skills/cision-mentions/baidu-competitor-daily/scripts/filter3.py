#!/usr/bin/env python3
"""filter3.py — 百度竞品同业日报 · 第一步：候选过滤。

读取原始监测数据（delta-bodies.xlsx）与翻译知识库（媒体名称表），按品牌/领导人别名匹配 +
多级剔除规则，产出 candidates.json。

关键口径：
  - 仅保留重点市场（中/美/英/中东等）
  - 仅收录英文内容（languageCode == 'en'）
  - 仅收录《翻译知识库》「媒体名称知识库」所列媒体（来源名做归一化）
  - 剔除新闻稿 / Press Release 电头
  - 国内企业 & 自动驾驶板块「全面收录」（额外允许正文命中）
"""
import argparse, openpyxl, re, json, collections

# ---------------- 1. 竞品 / 领导人别名表（可在此增删） ----------------
# 键为报告中的标准化实体名；值为匹配别名列表。
#   - 以 '~' 开头：子串正则（无词边界）
#   - 含中文：子串匹配
#   - 其他：词边界正则（避免误命中）
DOMESTIC_BRANDS = {
    '阿里巴巴/Alibaba': ['alibaba', '阿里巴巴'], '通义千问/Tongyi Qianwen': ['tongyi qianwen', 'tongyi', '通义'],
    'Qwen': ['qwen'], '阿福/Afu': ['阿福', ' afu'], '灵光/Lingguang': ['灵光', 'lingguang'],
    '蚂蚁集团/Ant Group': ['ant group', '蚂蚁', 'ant financial'], '字节跳动/ByteDance': ['bytedance', '字节跳动'],
    '抖音/Douyin': ['douyin', '抖音'], '豆包/Doubao': ['doubao', '豆包'], '火山引擎/Volcano Engine': ['volcano engine', '火山引擎'],
    'Seedance': ['seedance'], 'TikTok': ['tiktok'], '腾讯/Tencent': ['tencent', '腾讯'], '微信/WeChat': ['wechat', '微信'],
    '混元/Hunyuan': ['hunyuan', '混元'], '快手/Kuaishou': ['kuaishou', '快手'], '可灵/Kling': ['kling', '可灵'],
    '智谱/Zhipu': ['zhipu', '智谱'], 'MiniMax': ['minimax', '稀宇'], '月之暗面/Moonshot': ['moonshot', '月之暗面'],
    'Kimi': ['kimi'], '百川智能/Baichuan': ['baichuan', '百川'], '零一万物/01.AI': ['01.ai', '01ai', '零一万物'],
    '深度求索/DeepSeek': ['deepseek', '深度求索'], 'Manus': ['manus', '蝴蝶效应'], '华为/Huawei': ['huawei', '华为'],
    '沐曦/MetaX': ['metax', '沐曦'], '摩尔线程/Moore Threads': ['moore threads', '摩尔线程'], 'SHEIN/希音': ['shein', '希音'],
    '拼多多/Pinduoduo': ['pinduoduo', '拼多多'], 'PDD': ['pdd'], 'Temu': ['temu'], '小米/Xiaomi': ['xiaomi', '小米'],
    '商汤科技/SenseTime': ['sensetime', '商汤'], '京东/JD.com': ['jd.com', 'jd ', '京东'], '美团/Meituan': ['meituan', '美团'],
    '奇虎360/Qihoo 360': ['qihoo', '360 ', '奇虎'],
}
DOMESTIC_LEADERS = {
    '马云/Jack Ma': ['jack ma', '马云'], '蔡崇信/Joe Tsai': ['joe tsai', 'joseph tsai', '蔡崇信'],
    '吴泳铭/Eddie Wu': ['eddie wu', 'wu yongming', 'yongen wu', '吴泳铭'], '井贤栋/Eric Jing': ['jing xiandong', '井贤栋'],
    '张一鸣/Zhang Yiming': ['zhang yiming', '张一鸣'], '梁汝波/Liang Rubo': ['liang rubo', '梁汝波'],
    '周受资/Shou Zi Chew': ['shou zi chew', '周受资'], '马化腾/Pony Ma': ['pony ma', '马化腾'], '刘炽平/Martin Lau': ['martin lau', '刘炽平'],
    '黄峥/Colin Huang': ['colin huang', '黄峥'], '杨植麟/Zhilin Yang': ['zhilin yang', 'yang zhilin', '杨植麟'],
    '程一笑/Yixiao Cheng': ['yixiao cheng', 'cheng yixiao', '程一笑'], '闫俊杰/Yan Junjie': ['yan junjie', '闫俊杰'],
    '梁文锋/Liang Wenfeng': ['liang wenfeng', '梁文锋'],
}
AUTO_BRANDS = {
    'Waymo': ['waymo'], 'Cruise': [r"~(?<!tom )cruise(?![a-z0-9])(?!\s+(?:ship|ships|missile|missiles|control|line|lines|liner|cruiser|ship's))"], 'Zoox': ['zoox'], 'Wayve': ['wayve'], 'Uber': ['uber'],
    'WeRide/文远知行': ['weride', '文远知行'], 'PonyAI/小马智行': ['pony.ai', 'pony ai', 'ponyai', '小马智行'],
    'Caocao/曹操出行': ['caocao', '曹操出行'], 'XPeng/小鹏': ['xpeng', '小鹏'], 'Ruqi/如祺出行': ['ruqi', '如祺'],
    'Didi/滴滴': ['didi', '滴滴'], 'Lyft': ['lyft'], 'Cybercab': ['~cybercab'],
}
AUTO_LEADERS = {
    'Tekedra Mawakana (Waymo)': ['tekedra mawakana'], 'Dmitri Dolgov (Waymo)': ['dmitri dolgov'],
    'Aicha Evans (Zoox)': ['aicha evans'], 'Alex Kendall (Wayve)': ['alex kendall'],
    'Dara Khosrowshahi (Uber)': ['dara khosrowshahi'], '韩旭/Tony Han (WeRide)': ['tony han', '韩旭'],
    '彭军/James Peng (PonyAI)': ['james peng', '彭军'], '何小鹏/Xiaopeng He (XPeng)': ['xiaopeng he', '何小鹏'],
    'David Risher (Lyft)': ['david risher'], '埃隆·马斯克/Elon Musk': ['elon musk', '马斯克'],
}
OVERSEAS_BRANDS = {
    'Alphabet/Google': ['alphabet', 'google', 'gemini', 'deepmind', 'google deepmind'], 'Microsoft': ['microsoft'],
    'Meta': ['~(?<![a-z0-9])meta(?![a-z0-9A-Z\\-])'], 'Apple': ['apple'], 'Amazon': ['amazon'], 'Nvidia': ['nvidia'], 'IBM': ['ibm'], 'Intel': ['intel'],
    'Tesla': ['tesla'], 'OpenAI': ['openai'], 'Anthropic': ['anthropic'], 'Mistral': ['mistral'], 'Perplexity': ['perplexity'],
    'ChatGPT/GPT/Claude': ['chatgpt', 'chat gpt', ' gpt ', 'claude'],
}
OVERSEAS_LEADERS = {
    'Sundar Pichai (Alphabet/Google)': ['sundar pichai'], 'Demis Hassabis (DeepMind)': ['demis hassabis'],
    'Satya Nadella (Microsoft)': ['satya nadella'], 'Mark Zuckerberg (Meta)': ['mark zuckerberg'],
    'John Ternus (Apple)': ['john ternus'], 'Tim Cook (Apple)': ['tim cook'], 'Andy Jassy (Amazon)': ['andy jassy'],
    'Matt Garman (AWS)': ['matt garman'], 'Jeff Bezos (Amazon)': ['jeff bezos'], 'Jensen Huang (Nvidia)': ['jensen huang'],
    'Arvind Krishna (IBM)': ['arvind krishna'], 'Sam Altman (OpenAI)': ['sam altman'],
    'Dario Amodei (Anthropic)': ['dario amodei'], 'Bill Gates (Microsoft)': ['bill gates'],
}


def compile_aliases(d):
    out = {}
    for canon, alist in d.items():
        pats = []
        for a in alist:
            if a.startswith('~'):
                pats.append(('re', re.compile(a[1:], re.I)))
            elif re.search(r'[一-鿿]', a):
                pats.append(('sub', a))
            else:
                pats.append(('re', re.compile(r'(?<![a-z0-9])' + re.escape(a.strip()) + r'(?![a-z0-9])', re.I)))
        out[canon] = pats
    return out


C_DOM_B = compile_aliases(DOMESTIC_BRANDS); C_DOM_L = compile_aliases(DOMESTIC_LEADERS)
C_AUTO_B = compile_aliases(AUTO_BRANDS); C_AUTO_L = compile_aliases(AUTO_LEADERS)
C_OVB = compile_aliases(OVERSEAS_BRANDS); C_OVL = compile_aliases(OVERSEAS_LEADERS)


def parse_keywords(s):
    try:
        d = json.loads(s)
        if isinstance(d, dict):
            return d
    except Exception:
        pass
    return {}


def match_in_text(text_lower, compiled):
    found = []
    for canon, pats in compiled.items():
        for kind, p in pats:
            if kind == 'sub':
                if p in text_lower:
                    found.append(canon); break
            else:
                if p.search(text_lower):
                    found.append(canon); break
    return found


def kw_strong(kwdict, compiled):
    # keyword key with count >= 3
    found = []
    for canon, pats in compiled.items():
        for kind, p in pats:
            hit = False
            for k, c in kwdict.items():
                try:
                    cc = int(c)
                except Exception:
                    cc = 1
                if cc < 3:
                    continue
                kl = k.lower()
                if kind == 'sub' and p in kl:
                    hit = True; break
                if kind == 're' and p.search(kl):
                    hit = True; break
            if hit:
                found.append(canon); break
    return found


# ---------------- 2. 市场 / 媒体 ----------------
COUNTRY_MAP = {'Taiwan': 'China', 'England': 'United Kingdom'}
KEY_MARKETS = {'United States of America', 'United Kingdom', 'China', 'United Arab Emirates'}

# 数据来源名 -> KB 标准名（处理 Online 后缀 & 变体）
SRC_TO_KB = {
    'Bloomberg News Online': 'Bloomberg', 'Associated Press Online': 'The Associated Press',
    'The New York Times Online': 'The New York Times', 'The Wall Street Journal Online': 'The Wall Street Journal',
    'Financial Times Online': 'Financial Times', 'The Guardian Online': 'The Guardian',
    'The Times Online': 'The Times', "Barron's Online": "Barron's", 'Forbes Online': 'Forbes',
    'CNBC Online': 'CNBC', 'Fortune Online': 'Fortune', 'Reuters Online': 'Reuters',
    'BBC Zhongwen Trad': 'BBC', 'BBC Zhongwen Simp': 'BBC', 'BBC Zhongwen': 'BBC',
    'Wired Online': 'WIRED', 'Stag2.wired': 'WIRED', 'NPR/National Public Radio Online': 'NPR',
    'CBS News': 'CBS', 'CBS Local': 'CBS', 'CBS News Texas': 'CBS', 'CNN International Online': 'CNN',
    'Washington Post - Opinions': 'The Washington Post', 'Aljazeera International': 'AI Jazeera',
}


def market_ok(country, kb_media):
    return COUNTRY_MAP.get(country, country) in KEY_MARKETS


# ---------------- 3. 剔除规则 ----------------
EXCL = [
    ('Windows补丁/漏洞', re.compile(r'windows(?![a-z]).{0,40}(patch|vulnerab|exploit|cve|security fix|hotfix)', re.I)),
    ('安卓系统更新', re.compile(r'android(?![a-z]).{0,40}(update|upgrade|rollout|version|release|patch)', re.I)),
    ('谷歌手机', re.compile(r'pixel(?![a-z]).{0,30}(phone|smartphone|review|launch|price|camera)', re.I)),
    ('苹果手机', re.compile(r'iphone(?![a-z]).{0,30}(review|launch|price|camera|feature|sales|battery)', re.I)),
    ('苹果电脑', re.compile(r'macbook|imac|\bmac\b(?![a-z]).{0,40}(launch|book|computer|laptop|pro|air|mini|studio)', re.I)),
    ('医学', re.compile(r'(medical|clinical|vaccine|therap|drug discovery|pharmaceutical|healthcare ai)', re.I)),
    ('智能音箱', re.compile(r'(smart speaker|google home|amazon echo|\balexa\b|homepod|smart-speaker)', re.I)),
    ('市场报告/通稿噪音', re.compile(r'(market report|strategic business report|global .* market|analytics market|industry report|forecast to 203|cagr|syndicated)', re.I)),
    ('低价值/通稿', re.compile(r'(analyst calls|biggest analyst|price target|\bupgraded\b|\bdowngraded\b|podcast|robinhood|sba financing|selleramp|arbisource|independent amazon sellers|impact podcast)', re.I)),
    ('亚马逊雨林/河流(非公司)', re.compile(r'(rainforest|amazon river|amazon forest|amazon basin|the amazon\b)', re.I)),
    ('非Meta公司(metaEye/optics相机)', re.compile(r'(metaeye|meta-optics|metaoptics)', re.I)),
    ('苹果手机/硬件配件(低相关)', re.compile(r'(retail security brackets|security brackets for apple|iphone duo|apple homeview|ipad.{0,20}(bracket|case|cover))', re.I)),
    ('低价值股市噪音', re.compile(r'(etf.{0,40}adds|quality factor etf|adds apple and microsoft|intel q3 earnings preview: stock down|what is going on with intel stock|could a rally get president trump to highlight)', re.I)),
    ('低价值/无关内容', re.compile(r'(dear .* stock fans|mark your calendars for|how much traders expect .* stock to move|\$\d+ off right now|let the rationalizing begin|reminds .* investors of .* class action|securities class action lawsuit deadline|equity action reminder|lead plaintiff deadline|flippening|to do my job for a day|terra 6\.1|are \$?\d+ off)', re.I)),
]
EXCL_ECOMM = re.compile(r'(e-?commerce|warehouse|fulfillment|logistics|shipping|retail sales|online retail)', re.I)

# 新闻稿/通稿（Press Release）电头标记，扫描 标题/作者/摘要
PR_PAT = re.compile(r'(press ?release|prnewswire|pr newswire|globe ?newswire|einpresswire|ein ?presswire|business ?wire|news ?direct|marketwire|accesswire|prweb|issuewire|send2press|newsfile|cision|/pr ?newswire/)', re.I)


# ================= 2026-11-03 精细化口径（9 条） =================
# 1) Yahoo Finance 纯股价分析降噪：仅 source 含 yahoo 且为纯股价波动、无实质话题时剔除
YAHOO_STOCK_PAT = re.compile(r'(shares (?:rise|fall|jump|slip|drop|climb|tumble|soar|plunge|gain|lose|rally|slide|surge|sink|slump|edge|tick)|stock (?:rises|falls|jumps|slips|drops|climbs|tumbles|pops|slides|sinks|slumps|rallies|edges)|price target|upgraded|downgraded|buy rating|sell rating|analyst rating|stock price|market cap|catalyst|options trade|calls and puts|why .* stock)', re.I)
SUBSTANTIVE_PAT = re.compile(r'(\bai\b|artificial intelligence|\bagent\b|robotaxi|cybercab|robot|\bchip|semiconductor|cloud|\baws\b|autonomous|self-driving|fsd|model|earnings|revenue|profit|regulation|antitrust|lawsuit|probe|investigat|\bipo\b|funding|valuation|launch|partnership|deal|tariff|\bchina\b|political|election|trump|biden|senate|congress|white house)', re.I)

# 3) 马斯克 / 特斯拉话题门控
MUSK_TOPIC_DROP = re.compile(r'(starlink|spacex|\btwitter\b|on x\b|x platform|x corp|x social|grok(?!\s*ai))', re.I)
MUSK_TOPIC_KEEP = re.compile(r'(\bai\b|artificial intelligence|\bagent\b|robotaxi|cybercab|robot|\bchip|semiconductor|autonomous|self-driving|fsd|political|tariff|election|trump|biden|white house|senate|congress|regulation)', re.I)
TESLA_EV_REFRESH = re.compile(r'(tesla.{0,50}(new model|model refresh|redesign|facelift|next-?gen|all-new|updated model|updated version|refresh(?:ed)? model|generation|redesigned))', re.I)
TESLA_KEEP = re.compile(r'(fsd|robotaxi|cybercab|robot|\bchip|semiconductor|autonomous|self-driving|artificial intelligence|\bagent\b|\bai\b)', re.I)

# 4) Uber / Lyft 外卖业务剔除（保留自动驾驶/Robotaxi）
UBER_LYFT_DROP = re.compile(r'(uber\s+eats|ubereats|lyft\s+(?:delivery|pink|silver)|food delivery|meal delivery|delivery service|doordash|grubhub)', re.I)
UBER_LYFT_KEEP = re.compile(r'(robotaxi|autonomous|self-driving|driverless|waymo|zoox|cruise|\bav\b|self drive)', re.I)

# 5) 亚马逊电商/物流/外卖/消费硬件剔除（保留芯片/云/AI/Agent/自动驾驶）
AMAZON_DROP = re.compile(r'(amazon fresh|amazon grocery|whole foods|food delivery|e-?commerce|warehouse|fulfillment|logistics|shipping|retail sales|online retail|grocery|marketplace|third-party seller|best seller|all-time low|price drop|low price|on amazon|amazon\.com|echo show|echo dot|echo studio|\becho\b|\bkindle\b|\balexa\b|fire tv|doorbell|blink|astro|halo|smart display|smart alarm clock|smart speaker)', re.I)
AMAZON_KEEP = re.compile(r'(\bai\b|artificial intelligence|robot|autonomous|cloud|\baws\b|\bchip|semiconductor|model|agent|alexa ai|zoox|acquisition|merger|antitrust|regulator|\bfcc\b|lawsuit)', re.I)

# 6) 财报前瞻（仅剔前瞻，保留实际业绩）；配 ACTUAL_EARNINGS_PAT 防止误删实际业绩
EARNINGS_PREVIEW_PAT = re.compile(r'(earnings preview|results preview|quarterly preview|earnings watch|preview of (?:the |its |their |upcoming )?(?:earnings|quarterly|results)|ahead of (?:the |its |their |upcoming |this |next )?(?:earnings|results|report)|what to expect (?:from|as|when|before|around)|to report (?:its|their|first|second|third|fourth|q[1-4]|earnings)|before (?:the |its |their )?(?:earnings|results) report|is set to report|expected to report|will report|reports (?:its |their )?earnings (?:tomorrow|next|on |this |monday|tuesday|wednesday|thursday|friday|week)|everything you need to know (?:ahead|before)|earnings season preview|set to (?:release|announce) (?:its |their )?earnings|(?:earnings|results) on deck|on deck (?:thursday|wednesday|tuesday|monday|friday|as|for))', re.I)
ACTUAL_EARNINGS_PAT = re.compile(r'(reported|beats?|misses?|posted|quarterly (?:revenue|results|earnings)|q[1-4] (?:results|earnings|revenue)|full-year|fiscal (?:year|q)|earnings call|net income|operating income|raised (?:its |their )?guidance|beat estimates|missed estimates|topped|bottom line)', re.I)

# 7) 加密货币相关剔除
CRYPTO_PAT = re.compile(r'(cryptocurrency|\bcrypto\b|bitcoin|ethereum|blockchain|\bweb3\b|\bnft\b|defi|solana|dogecoin|coinbase|binance|crypto exchange|cryptocurrencies)', re.I)


def exclusion_reason(text, source, is_overseas):
    for name, pat in EXCL:
        if pat.search(text):
            return name
    if 'amazon' in text and EXCL_ECOMM.search(text) and not re.search(r'\bai\b|artificial intelligence|robot|autonomous|cloud|\baws\b|chip|semiconductor|model| alexa ai', text, re.I):
        return '亚马逊电商/物流(非AI)'
    return None


def topic_gate(dom_b, dom_l, auto_b, auto_l, ovb, ovl, title_l, excerpt_l, kwkeys_l, content_l, source):
    """2026-11-03 精细化口径：针对具体品牌/来源的话题门控，命中则返回剔除原因。"""
    # 1) Yahoo Finance 纯股价分析降噪
    if 'yahoo' in source.lower():
        blob = title_l + ' ' + kwkeys_l + ' ' + excerpt_l
        if YAHOO_STOCK_PAT.search(blob) and not SUBSTANTIVE_PAT.search(blob):
            return 'Yahoo 纯股价分析(降噪)'
    # 标题/摘要/关键词 作为强信号；正文(前段) 作为补充
    blob = title_l + ' ' + excerpt_l + ' ' + kwkeys_l + ' ' + content_l[:1800]
    # 2) 马斯克（领导人）话题门控：星链/SpaceX/推特等且不含重点话题 -> 剔除
    musk = any('musk' in e.lower() for e in (auto_l + ovl))
    if musk and MUSK_TOPIC_DROP.search(blob) and not MUSK_TOPIC_KEEP.search(blob):
        return '马斯克非重点话题(星链/SpaceX/推特等)'
    # 3) 特斯拉 电动车更新换代剔除（保留 FSD/Robotaxi/Cybercab/机器人/芯片/自动驾驶）
    tesla = any('tesla' in e.lower() for e in (ovb + dom_b + auto_b))
    if tesla and TESLA_EV_REFRESH.search(blob) and not TESLA_KEEP.search(blob):
        return '特斯拉电动车更新换代(非重点)'
    # 4) Uber / Lyft 外卖业务剔除（保留自动驾驶/Robotaxi）
    uber_lyft = any(('uber' in e.lower() or 'lyft' in e.lower()) for e in auto_b)
    if uber_lyft and UBER_LYFT_DROP.search(blob) and not UBER_LYFT_KEEP.search(blob):
        return 'Uber/Lyft 外卖业务(非重点)'
    # 5) 亚马逊电商/物流/外卖剔除（保留芯片/云/AI/Agent/自动驾驶）
    amazon = any('amazon' in e.lower() for e in ovb)
    if amazon and AMAZON_DROP.search(blob) and not AMAZON_KEEP.search(blob):
        return '亚马逊电商/物流/外卖(非AI)'
    # 6) 财报前瞻（仅剔前瞻，保留实际业绩）
    blob_head = title_l + ' ' + excerpt_l + ' ' + kwkeys_l
    if EARNINGS_PREVIEW_PAT.search(blob_head) and not ACTUAL_EARNINGS_PAT.search(blob_head):
        return '财报前瞻(非实际业绩)'
    # 7) 加密货币相关剔除（仅在标题/摘要/关键词强信号时）
    if CRYPTO_PAT.search(blob_head):
        return '加密货币相关'
    return None


def extract_impact(s):
    try:
        m = re.search(r'score:\s*([\d.]+)', str(s))
        return float(m.group(1)) if m else 0.0
    except Exception:
        return 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True, help='原始监测 xlsx，含 delta 工作表')
    ap.add_argument('--kb', required=True, help='翻译知识库.xlsx（含「媒体名称知识库」表）')
    ap.add_argument('--sheet', default='delta', help='工作表名，默认 delta')
    ap.add_argument('--out', default='candidates.json', help='候选输出 json')
    args = ap.parse_args()

    wb = openpyxl.load_workbook(args.input, read_only=True)
    ws = wb[args.sheet]
    rows = list(ws.iter_rows(values_only=True))
    header = rows[0]
    idx = {h: i for i, h in enumerate(header)}
    def col(r, n):
        v = r[idx[n]]
        return v if v is not None else ''

    # 仅收录 KB 媒体
    kb_wb = openpyxl.load_workbook(args.kb)
    kb_media = set(str(r[0]).strip() for r in kb_wb['媒体名称知识库'].iter_rows(min_row=2, values_only=True) if r[0])

    def src_norm(s):
        s = s.strip()
        if s in kb_media:
            return s
        if s.endswith(' Online') and s[:-7] in kb_media:
            return s[:-7]
        return SRC_TO_KB.get(s)

    results = []
    for r in rows[1:]:
        title = str(col(r, 'title')); source = str(col(r, 'source'))
        country = str(col(r, 'locationCountry')); lang = str(col(r, 'languageCode'))
        url = str(col(r, 'url')); pub = str(col(r, 'publishedAt'))
        excerpt = str(col(r, 'excerpt')); keywords = str(col(r, 'keywords'))
        author = str(col(r, 'author'))
        content = str(col(r, 'content')); impact = extract_impact(col(r, 'impactScore'))
        if not market_ok(country, kb_media):
            continue
        if lang.strip().lower() not in ('en', 'english'):
            continue
        media_kb = src_norm(source)
        if media_kb is None:
            continue
        if PR_PAT.search((title + ' ' + author + ' ' + excerpt).lower()):
            continue
        title_l = title.lower(); excerpt_l = excerpt.lower()
        kw = parse_keywords(keywords)
        kwkeys_l = ' '.join(k.lower() for k in kw.keys())
        excl_text = title_l + ' ' + kwkeys_l + ' ' + excerpt_l + ' ' + content.lower()[:1500]

        def placed(compiled, include_body=False):
            t = match_in_text(title_l, compiled)
            if t:
                return t
            e = match_in_text(excerpt_l, compiled)
            if e:
                return e
            k = kw_strong(kw, compiled)
            if k:
                return k
            if include_body:
                return match_in_text(content.lower()[:2500], compiled)
            return []

        dom_b = placed(C_DOM_B, include_body=True); dom_l = placed(C_DOM_L, include_body=True)
        auto_b = placed(C_AUTO_B); auto_l = placed(C_AUTO_L)
        ovb = placed(C_OVB); ovl = placed(C_OVL)

        is_overseas = bool(ovb or ovl)
        reason = exclusion_reason(excl_text, source, is_overseas)
        if not reason:
            reason = topic_gate(dom_b, dom_l, auto_b, auto_l, ovb, ovl,
                               title_l, excerpt_l, kwkeys_l, content.lower(), source)
        if reason:
            continue

        placements = []
        for c in (dom_b + dom_l):
            placements.append(('国内企业', c))
        for c in (auto_b + auto_l):
            placements.append(('自动驾驶', c))
        for c in ovb:
            placements.append(('海外企业', c))
        for c in ovl:
            placements.append(('企业领导人', c))
        if not placements:
            continue
        seen = set(); uniq = []
        for s, e in placements:
            if (s, e) in seen:
                continue
            seen.add((s, e)); uniq.append((s, e))
        results.append({'title': title, 'source': source, 'media_kb': media_kb, 'country': COUNTRY_MAP.get(country, country),
            'lang': lang, 'url': url, 'pub': pub, 'impact': impact,
            'dom_b': dom_b, 'dom_l': dom_l, 'auto_b': auto_b, 'auto_l': auto_l,
            'ovb': ovb, 'ovl': ovl, 'placements': uniq})

    # URL 去重（保留首次出现）
    seen_url = set(); deduped = []
    for x in results:
        if x['url'] in seen_url:
            continue
        seen_url.add(x['url']); deduped.append(x)
    results = deduped

    json.dump(results, open(args.out, 'w'), ensure_ascii=False, indent=1)
    sc = collections.Counter()
    ec = collections.Counter()
    for x in results:
        for s, e in x['placements']:
            sc[s] += 1; ec[(s, e)] += 1
    print('CANDIDATE COUNT:', len(results))
    print('Section:', dict(sc))
    for (s, e), c in sorted(ec.items()):
        print(f'  [{s}] {e}: {c}')
    print('Saved ->', args.out)


if __name__ == '__main__':
    main()
