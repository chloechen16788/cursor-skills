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
    '智谱/Zhipu': ['zhipu', '智谱'], 'MiniMax': ['minimax', '稀宇'],
    # 产品名一律归到所属公司：Kimi → 月之暗面/Moonshot
    '月之暗面/Moonshot': ['moonshot', '月之暗面', 'kimi'],
    '百川智能/Baichuan': ['baichuan', '百川'], '零一万物/01.AI': ['01.ai', '01ai', '零一万物'],    '深度求索/DeepSeek': ['deepseek', '深度求索'], 'Manus': ['manus', '蝴蝶效应'], '华为/Huawei': ['huawei', '华为'],
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
    'Waymo': ['waymo'], 'Zoox': ['zoox'], 'Wayve': ['wayve'], 'Uber': ['uber'],
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
    'Tesla': ['tesla'],
    # 产品名一律归到所属公司：ChatGPT/GPT → OpenAI，Claude → Anthropic
    'OpenAI': ['openai', 'open ai', 'chatgpt', 'chat gpt', 'gpt'],
    'Anthropic': ['anthropic', 'claude'],
    'Mistral': ['mistral'], 'Perplexity': ['perplexity'],
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
    'BNN Bloomberg Online': 'BNN Bloomberg', 'KNTV-TV Online': 'NBC Bay Area',
    'KPYX-TV Online': 'CBS', 'KOVR-TV Online': 'CBS',
}


def market_ok(country, kb_media):
    """重点市场判定。注意：媒体白名单优先于市场默认——已在《翻译知识库》媒体表内的
    媒体即为显式选定，其稿件不因所在国（新加坡/加拿大/澳洲等）被丢弃。
    该判断在调用处以「媒体是否在库」为前提，故此处保留纯国家判断供参考。"""
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
    ('财报电话会逐字稿(低价值)', re.compile(r'(earnings call transcript|transcript:\s|full transcript)', re.I)),
    ('生活/消费杂讯(低价值)', re.compile(r'(did you know you can use|abandons? (?:a )?patient|ambulance driver|options action:|takes? (?:an? )?uber (?:home|to)|tips? for riders|driver cancels ride|wrong direction mid-trip|passenger (?:says|claims)|phishing scam|beware of .{0,30}scam|impersonat)', re.I)),
    ('系统使用技巧(非竞争情报)', re.compile(r'windows (?:11|10)(?![a-z]).{0,50}(run better|performance|faster|8 ?gb|memory|requirements|upgrade|settings|tips)', re.I)),
    ('纯估值倍数评论(低价值)', re.compile(r'(forward p/e|price-to-earnings|p/e ratio)', re.I)),
    ('消费电子评测/导购', re.compile(r'(ipad|iphone|airpods|earbuds|apple watch|macbook|pixel|galaxy|surface|kindle|headphones|smartwatch|tablet|laptop).{0,45}(hands-on|review|should you buy|unboxing|first look|worth (?:it|buying)|i tried|tested)', re.I)),
    ('股评/荐股栏目', re.compile(r"(bulls vs\.? bears|money quote|heard on the street|cramer|stop trading|bloomberg talks|options action|stock movers|what'?s going on with .{0,30}stock|s&p 500 futures|top picks|trading ideas)", re.I)),
    ('分析师评级/目标价/荐股', re.compile(r'(price target|analyst (?:forecast|rating|note|sees|says|thinks)s?|top \d+ analyst|top analyst|here are \d+ top|\btrade the fear\b|buy rating|sell rating|\boverweight\b|\bunderweight\b|\d+% (?:upside|potential)|stock: |to \$?\d+\?|slowdown begin|stocks? to watch|stocks? making the biggest|shares remain attractive|longtime bull|bull who defends|steep valuation|mack daddy)', re.I)),
    ('消费硬件价格/规格', re.compile(r'(rtx \d|\bgpu\b.{0,25}(price|hike|shortage)|graphics card|gb of vram)', re.I)),
    ('财经视频/综述栏目', re.compile(r'^(?:watch |video:)| - bloomberg$|world in brief|in brief:', re.I)),
    ('广告/营销软文', re.compile(r'(shopping ads|tuning bids|more than scaling|advertorial|sponsored content)', re.I)),
    ('大盘/指数行情', re.compile(r'(s&p 500|nasdaq 100|stock futures|stock market today|market today|stocks set for|premarket trading|futures mixed|reverse gains to close|stocks moving (?:lower|higher)|biggest moves)', re.I)),
    ('律所/投资者公告', re.compile(r'(investor alert|lawsuit has been filed|class action|reminds .{0,30}investors|urges investors to contact|notifies investors)', re.I)),
    ('投资论点/估值', re.compile(r"(p/e ratio|p/e distortion|crown jewel|i'?m not touching|\bfomo\b|easy gains|is key for .{0,25}future|etf to own|outperform|valuation masks|questions? .{0,25}valuation)", re.I)),
    ('财经栏目/通讯', re.compile(r"(bloomberg tech:|cnbc's .{0,30}newsletter|fortune tech:|the china connection newsletter)", re.I)),
    ('亚马逊雨林/河流(非公司)', re.compile(r'(rainforest|amazon river|amazon forest|amazon basin|the amazon\b)', re.I)),
    ('非Meta公司(metaEye/optics相机)', re.compile(r'(metaeye|meta-optics|metaoptics)', re.I)),
    ('苹果手机/硬件配件(低相关)', re.compile(r'(retail security brackets|security brackets for apple|iphone duo|apple homeview|ipad.{0,20}(bracket|case|cover))', re.I)),
    ('低价值股市噪音', re.compile(r'(etf.{0,40}adds|quality factor etf|adds apple and microsoft|intel q3 earnings preview: stock down|what is going on with intel stock|could a rally get president trump to highlight)', re.I)),
    ('低价值/无关内容', re.compile(r'(dear .* stock fans|mark your calendars for|how much traders expect .* stock to move|\$\d+ off right now|let the rationalizing begin|reminds .* investors of .* class action|securities class action lawsuit deadline|equity action reminder|lead plaintiff deadline|flippening|to do my job for a day|terra 6\.1|are \$?\d+ off)', re.I)),
]
EXCL_ECOMM = re.compile(r'(e-?commerce|warehouse|fulfillment|logistics|shipping|retail sales|online retail)', re.I)

# Apple（水果）语境：菜谱/果园/果汁等；对照的科技语境用于排除误伤
APPLE_FOOD_PAT = re.compile(r'(recipe|chef|cook|bake|baking|dessert|orchard|apple cider|apple pie|baked apple|candy apple|fruit|mussels|chorizo|cider|harvest|variet(?:y|ies) of apple|apple tree)', re.I)
APPLE_TECH_PAT = re.compile(r'(iphone|ipad|macbook|\bmac\b|ios|macos|siri|tim cook|cupertino|app store|apple pay|apple watch|airpods|vision pro|apple intelligence|apple inc)', re.I)

# 新闻稿/通稿（Press Release）电头标记，扫描 标题/作者/摘要
PR_PAT = re.compile(r'(press ?release|prnewswire|pr newswire|globe ?newswire|einpresswire|ein ?presswire|business ?wire|news ?direct|marketwire|accesswire|prweb|issuewire|send2press|newsfile|cision|/pr ?newswire/)', re.I)


# ================= 精细化口径（9 条 + 后续修正） =================
# 1) Yahoo Finance 纯股价分析降噪：仅 source 含 yahoo 且为纯股价波动、无实质话题时剔除
YAHOO_STOCK_PAT = re.compile(r'(shares (?:rise|fall|jump|slip|drop|climb|tumble|soar|plunge|gain|lose|rally|slide|surge|sink|slump|edge|tick)|stock (?:rises|falls|jumps|slips|drops|climbs|tumbles|pops|slides|sinks|slumps|rallies|edges)|price target|upgraded|downgraded|buy rating|sell rating|analyst rating|stock price|market cap|catalyst|options trade|calls and puts|why .* stock)', re.I)
SUBSTANTIVE_PAT = re.compile(r'(\bai\b|artificial intelligence|\bagent\b|robotaxi|cybercab|robot|\bchip|semiconductor|cloud|\baws\b|autonomous|self-driving|fsd|model|earnings|revenue|profit|regulation|antitrust|lawsuit|probe|investigat|\bipo\b|funding|valuation|launch|partnership|deal|tariff|\bchina\b|political|election|trump|biden|senate|congress|white house)', re.I)

# 2) 马斯克（领导人）+ 特斯拉 话题门控：仅基于 标题+摘要+关键词（避免正文 transcript 污染）
#    剔除：星链/SpaceX/推特/X(Twitter)/Grok、特斯拉 EV/股价/销量 等非重点；
#    保留：AI/Agent/Robotaxi/Cybercab/FSD/芯片/自动驾驶/重大政治事件
MUSK_DROP = re.compile(r'(starlink|spacex|\btwitter\b|grok(?!\s*ai)|on\s+x\b|\bx\s+(?:platform|corp|social|ai|users?|faces|sues|scrutiny|the company|app)|tesla.{0,40}(?:ev|electric|vehicle|model|delivery|sales|car|cybertruck|refresh|update|record|production))', re.I)
MUSK_KEEP = re.compile(r'(\bai\b|artificial intelligence|\bagent\b|robotaxi|cybercab|\brobot\b|\bchip|semiconductor|autonomous|self-driving|\bfsd\b|political|election|trump|biden|white house|senate|congress|regulation|antitrust|lawsuit|doj|sec)', re.I)
TESLA_DROP = re.compile(r'tesla.{0,40}(?:sales|deliver|deliveries|stock|shares|price target|q[1-4]|earnings|production|gigafactory|factory|\bev\b|vehicles?|cars?|car\s|model\s|delivery|record|missed?|beat|cybertruck|update|refresh|redesign)', re.I)
TESLA_KEEP = re.compile(r'(fsd|robotaxi|cybercab|autonomous|self-driving|\bchip|semiconductor|\bai\b|artificial intelligence|\bagent\b|\brobot\b|dojo|optimus)', re.I)

# 3) Uber / Lyft 外卖业务剔除（保留自动驾驶/Robotaxi）
UBER_LYFT_DROP = re.compile(r'(uber\s+eats|ubereats|lyft\s+(?:delivery|pink|silver)|food delivery|meal delivery|delivery service|doordash|grubhub)', re.I)
UBER_LYFT_KEEP = re.compile(r'(robotaxi|autonomous|self-driving|driverless|waymo|zoox|cruise|\bav\b|self drive)', re.I)

# 4) 亚马逊：仅保留 AI/云/芯片/Agent/自动驾驶/机器人；其余（电商/广告/硬件/物流/偶发 AI 营销）剔除
#    注意：不使用裸 \bai\b（会命中 "AI 拍照亭" 等偶发 AI 营销），改用 substantive Amazon-AI 信号
# 不把裸 deal 当作保留词，否则 “Kindle deal” 会留下；芯片/云/并购类标题仍由 aws、chip、acquisition 等命中。
AMAZON_KEEP = re.compile(r'(artificial intelligence|alexa ai|\baws\b|cloud|bedrock|chip|semiconductor|agent|autonomous|self-driving|robot|zoox|generative|foundation model|\bllm\b|\banthropic\b|\bopenai\b|acquisition|merger|antitrust|regulator|\bfcc\b|lawsuit|\bdoj\b)', re.I)

# 5) 财报前瞻（仅剔前瞻，保留实际业绩）；ACTUAL 仅认“已公布业绩”措辞，避免 "Q3 earnings preview" 被误判为实际
EARNINGS_PREVIEW_PAT = re.compile(r'(earnings preview|results preview|quarterly preview|earnings watch|preview of (?:the |its |their |upcoming )?(?:earnings|quarterly|results)|ahead of (?:the |its |their |upcoming |this |next )?(?:earnings|results|report)|what to expect (?:from|as|when|before|around)|to report (?:its|their|first|second|third|fourth|q[1-4]|earnings)|before (?:the |its |their )?(?:earnings|results) report|is set to report|expected to report|will report|reports (?:its |their )?earnings (?:tomorrow|next|on |this |monday|tuesday|wednesday|thursday|friday|week)|everything you need to know (?:ahead|before)|earnings season preview|set to (?:release|announce) (?:its |their )?earnings|(?:earnings|results) on deck|on deck (?:thursday|wednesday|tuesday|monday|friday|as|for))', re.I)
ACTUAL_EARNINGS_PAT = re.compile(r'(reported|posted|beat|missed|topped|earnings call|net income|operating income|full-year|fiscal (?:year|quarter)|raised .{0,20}guidance|quarterly (?:revenue|results|earnings) (?:rose|fell|grew|declined|beat|missed|topped)|results (?:beat|missed|topped|came in)|revenue (?:rose|fell|grew|declined)|profit (?:rose|fell|grew|increased|decreased)|beat estimates|missed estimates)', re.I)

# 6) 加密货币相关剔除
CRYPTO_PAT = re.compile(r'(cryptocurrency|\bcrypto\b|bitcoin|ethereum|blockchain|\bweb3\b|\bnft\b|defi|solana|dogecoin|coinbase|binance|crypto exchange|cryptocurrencies)', re.I)

# Cruise（通用汽车自动驾驶品牌）匹配：仅当 "cruise" 与 GM/自动驾驶语境同现；剔除旅游/影讯等 "cruise"
CRUISE_TRAVEL = re.compile(r'\b(tom cruise|cruise ship|cruise ships|cruise line|cruise lines|river cruise|cruises? (?:ship|ships|line|lines|destination|vacation|holiday|activity)|mediterranean|caribbean|danube|rhine|transatlantic|antarctic|arctic|alaska(?:n)? cruise|box office|cinema|movie theater|\bfilm\b)', re.I)
CRUISE_AV_CTX = re.compile(r'\b(gm|robotaxi|self-driving|autonomous|driverless|waymo|\bav\b|self drive|gm cruise)\b', re.I)
def cruise_hit(t):
    # 仅凭标题判定：标题出现 cruise，且标题内带 AV 语境，且不是旅游/影讯/导弹。
    # 关键词字段（如 {"Cruise":12,"GM":5,"robotaxi":1} 的频次映射）不参与判定。
    head = t.lower()
    if CRUISE_TRAVEL.search(head):
        return False
    if not re.search(r'\bcruise\b', head):
        return False
    return bool(CRUISE_AV_CTX.search(head))


def is_broken_title(title):
    """监测导出偶有标题损坏：多条标题粘连、同一片段重复多次。
    这类条目无法用于报告（也无法翻译），直接剔除。"""
    t = title.strip()
    if len(t) > 220:
        return True
    low = t.lower()
    for n in (40, 30, 20):
        if len(low) < n * 2:
            continue
        head = low[:n]
        if head and low.count(head) >= 2:
            return True
    return False


def exclusion_reason(text, source, is_overseas):
    for name, pat in EXCL:
        if pat.search(text):
            return name
    # 苹果（水果/食材）与苹果公司同名：菜谱、果园、果汁类报道不得计入 Apple
    if re.search(r'\bapple\b', text) and APPLE_FOOD_PAT.search(text) and not APPLE_TECH_PAT.search(text):
        return '苹果(水果/食材，非公司)'
    if 'amazon' in text and EXCL_ECOMM.search(text) and not re.search(r'\bai\b|artificial intelligence|robot|autonomous|cloud|\baws\b|chip|semiconductor|model| alexa ai', text, re.I):
        return '亚马逊电商/物流(非AI)'
    return None


def topic_gate(dom_b, dom_l, auto_b, auto_l, ovb, ovl, title_l, excerpt_l, kwkeys_l, content_l, source):
    """精细化口径：针对具体品牌/来源的话题门控，命中则返回剔除原因。
    门控同样只凭「标题」判断，不读摘要/关键词/正文——与归属判定保持同一口径。"""
    head = title_l
    # 1) Yahoo Finance 纯股价分析降噪
    if 'yahoo' in source.lower():
        if YAHOO_STOCK_PAT.search(head) and not SUBSTANTIVE_PAT.search(head):
            return 'Yahoo 纯股价分析(降噪)'
    # 2) 马斯克（领导人）话题门控：星链/SpaceX/推特/X/Grok、特斯拉 EV 等非重点 -> 剔除
    musk = any('musk' in e.lower() for e in (auto_l + ovl))
    if musk and MUSK_DROP.search(head) and not MUSK_KEEP.search(head):
        return '马斯克非重点(星链/SpaceX/X/Twitter/Tesla-EV等)'
    # 3) 特斯拉 电动车/股价/销量 剔除（保留 FSD/Robotaxi/Cybercab/机器人/芯片/自动驾驶）
    tesla = any('tesla' in e.lower() for e in (ovb + dom_b + auto_b))
    if tesla and TESLA_DROP.search(head) and not TESLA_KEEP.search(head):
        return '特斯拉非重点(EV/股价/销量等)'
    # 4) Uber / Lyft 外卖业务剔除（保留自动驾驶/Robotaxi）
    uber_lyft = any(('uber' in e.lower() or 'lyft' in e.lower()) for e in auto_b)
    if uber_lyft and UBER_LYFT_DROP.search(head) and not UBER_LYFT_KEEP.search(head):
        return 'Uber/Lyft 外卖业务(非重点)'
    # 5) 亚马逊：仅保留 AI/云/芯片/Agent/自动驾驶/机器人，其余剔除
    amazon = any('amazon' in e.lower() for e in ovb)
    if amazon and not AMAZON_KEEP.search(head):
        return '亚马逊非AI/云/芯片(电商/广告/硬件等)'
    # 6) 财报前瞻：仅剔除「海外竞品」的前瞻稿；自动驾驶与国内竞品的前瞻保留
    #    （Uber/小鹏等无人驾驶相关前瞻含 robotaxi 投入信息，国内竞品前瞻亦作动态参考）
    if EARNINGS_PREVIEW_PAT.search(head) and not ACTUAL_EARNINGS_PAT.search(head):
        pure_overseas = bool(ovb) and not (auto_b or auto_l or dom_b or dom_l)
        if pure_overseas:
            return '财报前瞻(非实际业绩，海外竞品)'
    # 7) 加密货币相关剔除
    if CRYPTO_PAT.search(head):
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
        if lang.strip().lower() not in ('en', 'english'):
            continue
        media_kb = src_norm(source)
        if media_kb is None:
            continue
        # 媒体白名单优先：已在库的媒体即为显式选定，不受「重点市场」国家限制。
        # （新加坡《海峡时报》、加拿大 BNN 彭博、澳洲《澳大利亚人》均属此类）
        if is_broken_title(title):
            continue
        if PR_PAT.search((title + ' ' + author + ' ' + excerpt).lower()):
            continue
        title_l = title.lower(); excerpt_l = excerpt.lower()
        kw = parse_keywords(keywords)
        kwkeys_l = ' '.join(k.lower() for k in kw.keys())
        # 剔除判定不看关键词频次与正文（仅标题+摘要，摘要用于识别 PR 电头/硬件类）
        excl_text = title_l + ' ' + excerpt_l

        def placed(compiled):
            """仅凭「标题」判定品牌/领导人的归属。
            不看摘要、不看关键词频次、不看正文——关键词字段是「词→频次」映射，
            靠它归位会把 Qualcomm 财报挂到 Uber、Yum China 挂到 美团、
            Chevy Bolt 车评挂到 GM Cruise。标题点名才算该品牌的报道。"""
            return match_in_text(title_l, compiled)

        dom_b = placed(C_DOM_B); dom_l = placed(C_DOM_L)
        auto_b = placed(C_AUTO_B); auto_l = placed(C_AUTO_L)
        ovb = placed(C_OVB); ovl = placed(C_OVL)
        # Cruise（通用汽车自动驾驶品牌）：仅标题命中且带 AV 语境，剔除旅游/影讯
        if cruise_hit(title_l):
            if 'Cruise' not in auto_b:
                auto_b.append('Cruise')

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
