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
    # Moonshot 大小写敏感：公司名首字母大写（Moonshot AI / Moonshot）；小写 moonshot 多指登月计划
    '月之暗面/Moonshot': ['!(?<![A-Za-z])(?:Moonshot|MOONSHOT)(?![A-Za-z])', '月之暗面', 'kimi'],
    '百川智能/Baichuan': ['baichuan', '百川'], '零一万物/01.AI': ['01.ai', '01ai', '零一万物'],    '深度求索/DeepSeek': ['deepseek', '深度求索'], 'Manus': ['manus', '蝴蝶效应'], '华为/Huawei': ['huawei', '华为'],
    # —— 国内芯片/存储/光模块 ——
    # 这几家在《翻译知识库》品牌表里一直有中文名，但代码表未收录，稿件在归属环节被静默丢弃。
    '沐曦/MetaX': ['metax', '沐曦'], '摩尔线程/Moore Threads': ['moore threads', '摩尔线程'],
    '长鑫存储/CXMT': ['cxmt', '长鑫', 'changxin memory'],
    '长江存储/YMTC': ['ymtc', '长江存储', 'yangtze memory'],
    '天数智芯/Iluvatar': ['iluvatar', '天数智芯'],
    # Biren 是印度常见人名（如曼尼普尔首席部长 Biren Singh），故大小写敏感 + 排除该人名；
    # 大写 BIREN 为该公司在标题里的常见全大写写法
    '壁仞科技/Biren': ['!(?<![A-Za-z])(?:Biren|BIREN)(?![A-Za-z])(?!\\s+Singh)', 'biren technology', '壁仞'],
    '中际旭创/Innolight': ['innolight', '中际旭创', 'zhongji innoclight'],
    'SHEIN/希音': ['shein', '希音'],
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
    # Eric Schmidt：谷歌前 CEO/董事长。只收全名，不收裸 Schmidt（德语姓氏太常见，易误收）
    'Eric Schmidt (Alphabet/Google)': ['eric schmidt'],
}


def compile_aliases(d):
    """别名编译。前缀约定：
      '~' 后接自定义正则，大小写不敏感；
      '!' 后接自定义正则，**大小写敏感**（用于区分专有名词与普通词，如 Moonshot 公司 vs moonshot 登月）；
      其余按字面量加词边界，大小写不敏感。
    """
    out = {}
    for canon, alist in d.items():
        pats = []
        for a in alist:
            if a.startswith('~'):
                pats.append(('re', re.compile(a[1:], re.I)))
            elif a.startswith('!'):
                pats.append(('re', re.compile(a[1:])))
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


def match_in_text(text, compiled):
    """在文本中匹配别名表。

    传入**原始大小写**文本：别名表中 '!' 前缀的正则大小写敏感（用于 Moonshot 公司 vs moonshot 登月），
    若先转小写则永远匹配不到。其余正则均为 re.I，用原串同样正确；中文 'sub' 不受影响。
    """
    text_l = text.lower()
    found = []
    for canon, pats in compiled.items():
        for kind, p in pats:
            if kind == 'sub':
                if p in text:
                    found.append(canon); break
            else:
                if p.search(text):
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
    'Nikkei Asian Review': 'Nikkei Asia', 'Nikkei Asia Review': 'Nikkei Asia',
    # MarketWatch（道琼斯旗下财经站）在导出里可能带 Online 后缀或 .com 域名写法
    'MarketWatch Online': 'MarketWatch', 'MarketWatch.com': 'MarketWatch',
    'MarketWatch.com Online': 'MarketWatch', 'Dow Jones MarketWatch': 'MarketWatch',
    # —— 同一媒体的不同导出写法（KB 里已有该媒体，只是来源名对不上）——
    # 缺这层会让稿件被当作「未知媒体」静默丢弃：CNA 这一批就丢了 19 条英文稿。
    'CNA - CNA Digital': 'CNA', 'CNA Digital': 'CNA', 'Channel NewsAsia': 'CNA',
    'France24': 'France 24 English', 'France 24': 'France 24 English',
    'RFI - Radio France Internationale': 'RFI', 'RFI English': 'RFI',
    'BBC News Online': 'BBC', 'BBC News': 'BBC',
    # 地方台台号 → 所属电视网（与 KPYX/KOVR → CBS 同理）
    'WPSG-TV Online': 'CBS', 'WCBS-TV Online': 'CBS', 'KCBS-TV Online': 'CBS',
    'WBBM-TV Online': 'CBS', 'KNXT-TV Online': 'CBS',
    'WNBC-TV Online': 'NBC News', 'WCAU-TV Online': 'NBC News', 'KNBC-TV Online': 'NBC News',
    # 自动驾驶垂媒（导出可能带域名或 Online 后缀）
    'InsideEVs.com': 'InsideEVs', 'Inside EVs': 'InsideEVs', 'InsideEVs Online': 'InsideEVs',
    'Electrek.co': 'Electrek', 'Electrek Online': 'Electrek', 'Electrek.co Online': 'Electrek',
    # 历史写法兼容（KB 标准写法为 Tech in Asia）
    'Tech In Asia': 'Tech in Asia',
}


# ===== 领导人归入所属品牌 =====
# section 仍只用发布脚本认识的四个名字。能解析到品牌的领导人写入该品牌所在板块
# （国内企业 / 自动驾驶 / 海外企业），不再写入「企业领导人」。
# 无法确定所属品牌时保留为独立实体，留在默认板块，不丢条目。
BRAND_SECTION = {}
for _c in DOMESTIC_BRANDS:
    BRAND_SECTION[_c] = '国内企业'
for _c in AUTO_BRANDS:
    BRAND_SECTION[_c] = '自动驾驶'
for _c in OVERSEAS_BRANDS:
    BRAND_SECTION[_c] = '海外企业'

# 领导人实体括号内标注的公司名，有些不是品牌表里的 canon 名，需要归一
LEADER_PARENT_ALIAS = {
    'DeepMind': 'Alphabet/Google', 'Google DeepMind': 'Alphabet/Google',
    'Alphabet': 'Alphabet/Google', 'Google': 'Alphabet/Google',
    'AWS': 'Amazon',
    'WeRide': 'WeRide/文远知行', 'PonyAI': 'PonyAI/小马智行', 'XPeng': 'XPeng/小鹏',
}

# 实体名里没有括号的领导人（国内领导人多为「中文名/英文名」）需显式指定所属品牌。
# Elon Musk 横跨 Tesla / SpaceX / X / xAI，没有单一归属，保留为独立实体（仍在自动驾驶板块）。
LEADER_PARENT = {
    '马云/Jack Ma': '阿里巴巴/Alibaba', '蔡崇信/Joe Tsai': '阿里巴巴/Alibaba',
    '吴泳铭/Eddie Wu': '阿里巴巴/Alibaba', '井贤栋/Eric Jing': '蚂蚁集团/Ant Group',
    '张一鸣/Zhang Yiming': '字节跳动/ByteDance', '梁汝波/Liang Rubo': '字节跳动/ByteDance',
    '周受资/Shou Zi Chew': 'TikTok', '马化腾/Pony Ma': '腾讯/Tencent',
    '刘炽平/Martin Lau': '腾讯/Tencent', '黄峥/Colin Huang': '拼多多/Pinduoduo',
    '杨植麟/Zhilin Yang': '月之暗面/Moonshot', '程一笑/Yixiao Cheng': '快手/Kuaishou',
    '闫俊杰/Yan Junjie': 'MiniMax', '梁文锋/Liang Wenfeng': '深度求索/DeepSeek',
    '埃隆·马斯克/Elon Musk': None,
}


def leader_parent(canon):
    """取领导人的所属公司：优先查显式表，其次解析实体名里的括号标注。"""
    if canon in LEADER_PARENT:
        return LEADER_PARENT[canon]
    m = re.search(r'[(（]\s*([^)）]+?)\s*[)）]', canon)
    if not m:
        return None
    p = m.group(1).strip()
    return LEADER_PARENT_ALIAS.get(p, p)


def leader_placement(canon, default_section):
    """领导人 → (板块, 品牌实体)；找不到所属品牌时退回自身实体，避免条目被丢。"""
    p = leader_parent(canon)
    if p and p in BRAND_SECTION:
        return (BRAND_SECTION[p], p)
    return (default_section, canon)


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
    ('分析师评级/目标价/荐股', re.compile(r'(price target|analyst (?:forecast|rating|note|sees|says|thinks)s?|top \d+ analyst|top analyst|here are \d+ top|\btrade the fear\b|buy rating|sell rating|\boverweight\b|\bunderweight\b|\d+% (?:upside|potential)|stock: |to \$?\d+\?|slowdown begin|stocks? to (?:watch|buy|own|hold|sell)|stocks? making the biggest|scoops? up|ark (?:sells|buys)|implodes|sheds \$|forget \w+: why|safe haven|long-term investors|next \d+ trading days|watchlist|bullpen|shares remain attractive|longtime bull|bull who defends|steep valuation|mack daddy|absurdly cheap|deeply undervalued|hidden gem|worth buying now|is a buy\b|time to buy|overvalued|undervalued|fair value)', re.I)),
    ('消费硬件价格/规格', re.compile(r'(rtx \d|\bgpu\b.{0,25}(price|hike|shortage)|graphics card|gb of vram)', re.I)),
    ('财经视频/综述栏目', re.compile(r'^(?:watch |video:)| - bloomberg$|world in brief|in brief:', re.I)),
    ('广告/营销软文', re.compile(r'(shopping ads|tuning bids|more than scaling|advertorial|sponsored content)', re.I)),
    ('大盘/指数行情', re.compile(r'(s&p 500|nasdaq 100|stock futures|(?:dow|nasdaq|s&p)\s+(?:jones\s+)?futures|stock market today|market today|stocks set for|premarket trading|futures mixed|reverse gains to close|stocks moving (?:lower|higher)|biggest moves)', re.I)),
    ('律所/投资者公告', re.compile(r'(investor alert|lawsuit has been filed|class action|reminds .{0,30}investors|urges investors to contact|notifies investors)', re.I)),
    ('投资论点/估值', re.compile(r"(p/e ratio|p/e distortion|crown jewel|i'?m not touching|\bfomo\b|easy gains|is key for .{0,25}future|etf to own|outperform|valuation masks|questions? .{0,25}valuation)", re.I)),
    ('财经栏目/通讯', re.compile(r"(bloomberg tech:|cnbc's .{0,30}newsletter|fortune tech:|the china connection newsletter)", re.I)),
    ('亚马逊雨林/河流(非公司)', re.compile(r'(rainforest|amazon river|amazon forest|amazon basin|the amazon\b)', re.I)),
    ('非Meta公司(metaEye/optics相机)', re.compile(r'(metaeye|meta-optics|metaoptics)', re.I)),
    ('苹果手机/硬件配件(低相关)', re.compile(r'(retail security brackets|security brackets for apple|iphone duo|apple homeview|ipad.{0,20}(bracket|case|cover))', re.I)),
    ('低价值股市噪音', re.compile(r'(etf.{0,40}adds|quality factor etf|adds apple and microsoft|intel q3 earnings preview: stock down|what is going on with intel stock|could a rally get president trump to highlight)', re.I)),
    # —— 散户理财/股价推算：只教人算收益、猜底、择时，无竞争情报 ——
    # 与「股评/荐股」「投资论点/估值」互补：那两条抓栏目与评级，这条抓散户视角的股价文。
    ('散户股价推算/择时', re.compile(
        r'(if you (?:had )?invested \$|what history suggests is the floor'
        r'|cheaper than a (?:toilet|toilet-paper|cigarette|beer)'
        r'|\boptions traders\b|\bputs? and calls?\b|is now down (?:this|for the) year'
        r'|stock is back down at|share (?:dip|slide|drop)\b.{0,30}(?:trigger|wider|selloff)'
        r'|\bbuy \w+ or \w+\?|look like bargains?|\bthe floor\b'
        r'|time to (?:buy|sell) (?:the )?(?:dip|stock)|is it time to buy'
        r'|cathie wood (?:buys|sells|adds|trims)|buys? \$[\d.,]+ million of'
        r'|warning for investors|investors heading into \d{4}'
        r'|^opinion\s*[|:])', re.I)),

    # —— intel = 「情报」而非 Intel 公司 ——
    ('intel=情报(非Intel公司)', re.compile(
        r'\bintel (?:report|reports|assessment|community|agencies|agency|official|officials|briefing|source)\b'
        r'|\bin intel\b|\bintel report\b', re.I)),

    # —— 本地商家好评/SEO 软文（Google Reviews 与科技公司无关）——
    ('本地商家好评软文', re.compile(
        r'google reviews?\b.{0,60}(?:home sellers?|realtor|roofing|plumb|dentist|law firm|pest control|hvac)'
        r'|reviews? recognize .{0,50}(?:for (?:honest|excellent|outstanding)|home sellers?)'
        r'|\bgoogle reviews? recognize\b', re.I)),

    # —— 罪案/司法花边（与公司业务无关的个案）——
    ('罪案/司法花边', re.compile(
        r'found guilty for (?:threatening|murder|assault)|murder-for-hire'
        r'|catches? (?:a )?thief|home invasion|carjacking|caught (?:stealing|shoplifting)'
        r'|sentenced to \d+ years|arrested for (?:threatening|assault)', re.I)),

    # —— 致富教程/副业指南 ——
    ('致富教程/副业指南', re.compile(
        r'turn your .{0,30} into a \$|into a \$[\d,]+ (?:business|side hustle|income)'
        r'|how to (?:make|earn) \$[\d,]+ (?:a|per) (?:month|week|day)'
        r'|start (?:a|your) \$[\d,]+ (?:business|side hustle)', re.I)),

    # —— 娱乐/职业转型花边 ——
    ('娱乐/职业转型花边', re.compile(
        r'made the move from \w+ to (?:tv|film|hollywood)|comedy star .{0,40}(?:tiktok|youtube)'
        r'|from (?:tiktok|youtube|instagram) to (?:tv|film|hollywood)', re.I)),

    # —— 软件 bug/更新日志（非产品战略）——
    ('软件bug/更新日志', re.compile(
        r'copy-paste bug|\bbug\b.{0,30}(?:reintroduc|fixed|fixed it)'
        r'|excel \d{4}|office \d{4}|seasonal clock change|daylight saving'
        r'|(?:fixed|patched) (?:a )?(?:bug|issue).{0,40}(?:then|now)', re.I)),

    # —— 富豪榜/豪宅地产 ——
    ('富豪榜/地产花边', re.compile(
        r'billionaire (?:ranking|rankings|list|magnet|enclave)|drops? to no\. \d+ in'
        r'|created \d+ billionaires?|\d+ billionaires? worth'
        r'|\bnet worth\b.{0,40}(?:ranking|list|falls|drops)', re.I)),

    # —— 通稿/SEO 换皮（小站转载、产品上架贴）——
    ('通稿/SEO换皮', re.compile(
        r'\bxinhua silk road\b|integrates openai.{0,40}(?:a day after|running)'
        r'|\baivideofree\b|\bfreddy\b x google|logo new website|now available on .{0,20}marketplace', re.I)),

    # —— 怀旧开箱/复古测评 ——
    ('怀旧开箱/复古测评', re.compile(
        r'(?:back|return) to unboxing|unboxing a geforce|nostalgia|throwback to \d{4}', re.I)),

    # —— 个人使用技巧（非产品战略）——
    # 注意：客户明确要求保留 Apple Intelligence / Siri 的评测与上手稿并加权，
    # 故此处用负向前瞻把它们排除在外，避免误伤。
    ('个人使用技巧/教程', re.compile(
        r'^(?!.*(?:apple intelligence|\bsiri\b|\bai\b))'
        r'(?:how i (?:use|set up|trick)|how to use (?:your|my)|tips? (?:and tricks )?for (?:using|getting)'
        r'|without (?:opening|needing)|step[- ]by[- ]step guide to (?:using|setting up))', re.I)),

    # —— 第一人称走访/见闻（非产业情报）——
    ('第一人称走访/见闻', re.compile(
        r'^i (?:went to|visited|spent a day|sat down with)|everyone (?:talked|was talking) about'
        r'|what i (?:learned|saw) (?:at|from) (?:a|an|the) ', re.I)),

    # —— 社媒使用场景/公益宗教（平台被使用，非平台经营）——
    ('社媒使用场景/公益', re.compile(
        r'missionar|take to (?:tiktok|instagram|youtube|facebook) to reach'
        r'|to reach younger generations|church|parish|charity drive', re.I)),

    ('低价值/无关内容', re.compile(r'(dear .* stock fans|mark your calendars for|how much traders expect .* stock to move|\$\d+ off right now|let the rationalizing begin|reminds .* investors of .* class action|securities class action lawsuit deadline|equity action reminder|lead plaintiff deadline|flippening|to do my job for a day|terra 6\.1|are \$?\d+ off)', re.I)),
    # 律所/事故索赔广告（非公司新闻）："Car Accident Attorney Explains Uber Claims" 之类
    ('律所/事故索赔广告', re.compile(r'(accident attorney|accident lawyer|injury attorney|injury lawyer|car accident|truck accident|personal injury|claims? (?:against|for) .{0,20}(uber|lyft)|free consultation|no win no fee)', re.I)),
    # 商业软文/产品上架：合作伙伴获奖、Marketplace 上架、集成公告
    ('商业软文/产品上架', re.compile(r'(wins? (?:two |three )?\d{4} .{0,30}awards?|partner awards?|is now available on .{0,30}marketplace|announces? (?:the )?(?:launch|availability) of .{0,30}(?:on|in) .{0,20}marketplace|logo new website|otc:|brings .{0,45}into .{0,30}(?:management|platform)|integrates .{0,30}into its platform)', re.I)),
    # 生活/情感专栏（AI 陪伴、情感建议类，非产业情报）
    ('生活/情感专栏', re.compile(r'(dating advice|ask ai for|my (?:love|dating) life|relationship advice|should you (?:date|marry)|friends to stay with|is it rude|sparks? a debate|my \d+ .{0,25}speakers)', re.I)),
    # 个人理财/攻略清单：用 AI 赚钱/还债/致富类点击文
    ('个人理财/攻略', re.compile(r'(\d+\s+(?:chatgpt|gemini|claude|copilot) prompts?|prompts? to (?:get out of debt|make money|build wealth|save money)|get out of debt|build(?:ing)? wealth|start (?:a|your) (?:side hustle|business) with ai|make \$?\d+ (?:a|per) (?:day|week|month) with ai)', re.I)),
    # 清单体/调侃文：N 种方式、N 件事、N 个教训——无产业信息
    ('清单体/调侃文', re.compile(r'(\b\d+\s+(?:better |best |worst |other |more )?(?:ways|things|reasons|lessons|signs|rules|habits|mistakes|questions)\b|\bcould have (?:wasted|spent|done)\b|what we can learn from)', re.I)),
    # 他业类比「XX 界的 Uber」：主语不是本公司，属比喻式报道
    ('人物/影视访谈', re.compile(r'(on life since|since the release of (?:his|her)|the man who inspired|the woman who inspired|talks? about (?:his|her) new (?:film|book))', re.I)),
    ('他业类比(非本公司)', re.compile(r'(?:the|an?)\s+["“]?uber of\b|\buber for\b|\buber-of-', re.I)),
]
EXCL_ECOMM = re.compile(r'(e-?commerce|warehouse|fulfillment|logistics|shipping|retail sales|online retail)', re.I)

# 以下规则**只作用于标题**。它们描述的是「报道体裁」（股评、行情快讯、促销、评测、估值评论），
# 体裁特征必然体现在标题上；若连摘要一起扫，摘要里常见的 "premarket trading"、
# "discount platform"、"movie" 等词会造成误剔（实例：Apple 内存涨价稿因摘要含 premarket trading 被剔）。
TITLE_ONLY_RULES = {
    '大盘/指数行情', '股评/荐股栏目', '分析师评级/目标价/荐股', '消费电子评测/导购',
    '消费硬件价格/规格', '纯估值倍数评论(低价值)', '投资论点/估值', '财经栏目/通讯',
    '财经视频/综述栏目', '系统使用技巧(非竞争情报)', '广告/营销软文', '低价值股市噪音',
    '财报电话会逐字稿(低价值)', '生活/消费杂讯(低价值)', '律所/事故索赔广告',
    '商业软文/产品上架', '生活/情感专栏', '个人理财/攻略', '清单体/调侃文', '他业类比(非本公司)', '人物/影视访谈',
    # 以下为标题层面的体裁判断，只看标题（摘要里常有股价/评论语境，一并扫会误剔实质稿）
    '散户股价推算/择时', 'intel=情报(非Intel公司)', '本地商家好评软文', '罪案/司法花边',
    '致富教程/副业指南', '娱乐/职业转型花边', '软件bug/更新日志', '富豪榜/地产花边',
    '通稿/SEO换皮', '怀旧开箱/复古测评', '个人使用技巧/教程', '社媒使用场景/公益',
}

# 纯政治评论：选举horse-race、民调、党派攻防——不含任何商业/AI/产品信号时无竞争情报价值。
# 仅当标题同时出现商业信号（合同/监管/估值/产品/公司经营）时才保留。
POLITICS_PAT = re.compile(
    r'(midterm|mid-term|election day|election result|blue wave|red wave|\bvoters?\b|ballot|'
    r'poll(?:s|ing)?\b|gop|democrat|republican|senate race|primary race|trump|biden|'
    r'political fortune|spent \$|spending \$|spend \$|donor|pac\b|super pac|endors(?:e|ed|ement)|'
    r'campaign|inaugurat|swing state|texas turns blue|vote red|lost the election|election bet|'
    r'\bdoge\b|lawyer up|persecut|political retribution|'
    r'midterms failure|political party|talarico|mamdani|sanders accuses|politics|\bsenate\b|\bcongress\b|campaign trail|re-election bid)', re.I)
# 强政治判据：选举结果/党争攻防/政治报复类叙事，即使提到股价代码或 AI 监管，
# 也不是产业情报——这些词本身就是「政治故事」的标记，故命中即剔，不被 BUSINESS_SIGNAL 豁免。
# 注意不包含裸 `after the midterm`：那会误伤「选举后特斯拉股价为何下跌」这类市场影响稿，
# 后者此前已确认保留。
STRONG_POLITICS_PAT = re.compile(
    r'midterm rout|persecut|governor-elect|election night|fires back at (?:democrats|republicans|critics)'
    r'|spent (?:at least )?\$[\d.,]+ million in|lawyer up|political retribution|\bdoge\b'
    r'|loses? billions', re.I)

BUSINESS_SIGNAL_PAT = re.compile(
    r'(\bai\b|artificial intelligence|\bchip|semiconductor|datacent|data cent|robotaxi|'
    r'self-driving|autonomous|\brobot\b|contract|tariff|antitrust|lawsuit|\bdoj\b|\bftc\b|\bsec\b|'
    r'regulation|regulator|\bipo\b|valuation|revenue|earnings|guidance|\bproduct\b|model|'
    r'satellite|starlink|spacex|tesla|\bspcx\b|xai|grok|\bx\.ai\b|wireless|spectrum|launch)', re.I)

# 促销/折扣/导购（只看标题）：任何品牌的纯促销都无竞争情报价值。
# 不能用裸 deal（"ADNOC OpenAI Deal" 是商业交易）、裸 sale（"sales" 是销售额）、
# 裸 discount（"discount shopping platform" 指折扣电商模式）。
# —— 芯片/存储/供应链价格 ≠ 零售促销 ——
# "Memory chip price drop squeezes CXMT margins"、"GPU price hikes boost Biren" 是核心竞争情报，
# 但裸 `price drop/cut` 与 `\bgpu\b.{0,25}(price|hike)` 会把它们当成促销/消费硬件价格剔掉。
# 判据：出现价格变动 + 供应链主体（DRAM/NAND/晶圆/GPU/芯片…）且**不含消费电子整机**（iPhone/Pixel/耳机…）→ 视为情报。
PRICE_MOVE_PAT = re.compile(
    r'(?:price|pricing|cost)s?\s*(?:drop|cut|hike|rise|surge|slump|decline|war|pressure)'
    r'|(?:drop|cut|hike|raise|lower|slash)s?\b.{0,20}\b(?:price|pricing)', re.I)
SUPPLY_SUBJECT_PAT = re.compile(
    r'\b(?:dram|nand|hbm|wafer|foundry|node|capacity|asp|contract|spot|inventory|memory'
    r'|chip|chips|semiconductor|gpu|cpu|accelerator|optical module|laser|substrate)\b', re.I)
CONSUMER_DEVICE_PAT = re.compile(
    r'\b(?:iphone|ipad|macbook|pixel|galaxy|airpods|earbuds|apple watch|watch series|kindle|echo'
    r'|fire tv|surface|headphones|smartwatch|laptop|tablet|console|ps5|xbox|nest|chromecast|buds)\b', re.I)


def supply_price_intel(head):
    """标题是否为「芯片/存储/供应链价格变动」这类竞争情报（而非零售促销）。"""
    if not PRICE_MOVE_PAT.search(head):
        return False
    if CONSUMER_DEVICE_PAT.search(head):
        return False          # 明确指向消费电子整机 → 仍按促销处理
    return bool(SUPPLY_SUBJECT_PAT.search(head))


PROMO_PAT = re.compile(
    r'(\$\d[\d,]*\s*off|\d+\s*(?:%|percent)\s*off|price (?:drop|cut|slashes?)\b|record[- ]low(?:est)? price|lowest price (?:ever|yet)'
    r'|black friday|cyber monday|prime (?:day|big deal day)|\bbest .{0,25}deals?\b|deals? of the (?:day|week)'
    r'|discount code|\bcoupon\b|save \$\d|gift guide|already on sale|\bon sale (?:now|for|at)\b|\bclearance\b|flash sale'
    r'|drops? to \$\d|slashed? to \$\d'
    r'|(?:echo dot|echo show|kindle|fire tv|fire tablet|fire stick|ring (?:camera|doorbell)|\bblink\b|\beero\b'
    r'|nest (?:hub|cam|thermostat)|chromecast|pixel buds|pixel \d+\w?|apple tv 4k|airpods|apple watch|ipad|iphone|macbook)'
    r'.{0,45}(price (?:drop|cut|slashes?)|record[- ]low|\$\d[\d,]*\s*off|\d+%\s*off|\bcoupon\b|drops? to \$\d))',
    re.I)

# Apple（水果）语境：菜谱/果园/果汁等；对照的科技语境用于排除误伤
APPLE_FOOD_PAT = re.compile(r'(recipe|chef|cook|bake|baking|dessert|orchard|apple cider|apple pie|baked apple|candy apple|fruit|mussels|chorizo|cider|harvest|variet(?:y|ies) of apple|apple tree)', re.I)
APPLE_TECH_PAT = re.compile(r'(iphone|ipad|macbook|\bmac\b|ios|macos|siri|tim cook|cupertino|app store|apple pay|apple watch|airpods|vision pro|apple intelligence|apple inc)', re.I)

# Apple 影视内容（Apple TV+ 剧集/电影）——属内容业务，非硬件或 AI 竞争情报
APPLE_MEDIA_PAT = re.compile(r'(apple\s*tv\+|apple\s*tv\b(?!\s*4k)|apple studios|apple original|(?:tv|television) (?:series|show|drama|comedy|thriller)|streaming (?:series|show)|renews? .{0,30}for season|season \d+|episode \d|box office|emmy|oscar|golden globe|documentary|premiere)', re.I)

# 登月计划 vs 月之暗面：登月语境（NASA/moon/lunar/spacecraft）优先，且该 moonshot 为小写或非公司语境
LUNAR_PAT = re.compile(r'(\bnasa\b|\bmoon\b|lunar|spacecraft|space mission|rocket|artemis|apollo|orbit|astronaut|spacex 星舰|登月|月球)', re.I)
MOONSHOT_COMPANY_PAT = re.compile(r'(moonshot\s*(?:ai|kimi)|kimi|月之暗面|\bai startup\b|\bllm\b|large language model|杨植麟|zhilin)', re.I)

# 新闻稿/通稿（Press Release）电头标记，扫描 标题/作者/摘要
PR_PAT = re.compile(r'(press ?release|prnewswire|pr newswire|globe ?newswire|einpresswire|ein ?presswire|business ?wire|news ?direct|marketwire|accesswire|prweb|issuewire|send2press|newsfile|cision|/pr ?newswire/)', re.I)


# ================= 精细化口径（9 条 + 后续修正） =================
# 1) Yahoo Finance 纯股价分析降噪：仅 source 含 yahoo 且为纯股价波动、无实质话题时剔除
YAHOO_STOCK_PAT = re.compile(r'(shares (?:rise|fall|jump|slip|drop|climb|tumble|soar|plunge|gain|lose|rally|slide|surge|sink|slump|edge|tick)|stock (?:rises|falls|jumps|slips|drops|climbs|tumbles|pops|slides|sinks|slumps|rallies|edges)|price target|upgraded|downgraded|buy rating|sell rating|analyst rating|stock price|market cap|catalyst|options trade|calls and puts|why .* stock)', re.I)
SUBSTANTIVE_PAT = re.compile(r'(\bai\b|artificial intelligence|\bagent\b|robotaxi|cybercab|robot|\bchip|semiconductor|memory|dram|nand|margin|pricing|supply chain|cloud|\baws\b|autonomous|self-driving|fsd|model|earnings|revenue|profit|guidance|outlook|regulation|antitrust|lawsuit|probe|investigat|\bipo\b|(?:trading|market|exchange)\s+debut|funding|valuation|launch|partnership|deal|tariff|\bchina\b|political|election|trump|biden|senate|congress|white house)', re.I)

# 纯股价波动（不限来源）：标题只描述股价涨跌/评级，无实质议题时剔除。
# 注意只匹配「股票/股价 + 涨跌动词」这种结构，避免误伤 "sales rise"（销售额增长）等实质数据。
STOCK_MOVE_PAT = re.compile(
    r'(\b(?:stock|shares?)\s+(?:rises?|falls?|jumps?|slips?|drops?|climbs?|tumbles?|pops?|slides?|sinks?|slumps?|rallies|edges?|surges?|soars?|plunges?|gains?|loses?|ticks?|wavers?|retreats?)\b'
    r'|\b(?:stock|shares?)\s+(?:climb|rise|fall|drop|jump|slide)s?\s+(?:amid|as|on|after)\b'
    r'|what(?:\'s| is| are)?\s+going on with .{0,30}stock|stock (?:price|movement)s?\b|market cap (?:falls|rises|drops|tops)\b'
    r'|\bpremarket\b|\bafter-hours\b)',
    re.I)

# 2) 马斯克（领导人）+ 特斯拉 话题门控：仅基于 标题+摘要+关键词（避免正文 transcript 污染）
#    剔除：星链/SpaceX/推特/X(Twitter)/Grok、特斯拉 EV/股价/销量 等非重点；
#    保留：AI/Agent/Robotaxi/Cybercab/FSD/芯片/自动驾驶/重大政治事件
MUSK_DROP = re.compile(r'(starlink|spacex|starship|\btwitter\b|grok(?!\s*ai)|on\s+x\b|\bx\s+(?:platform|corp|social|ai|users?|faces|sues|scrutiny|the company|app)|tesla.{0,40}(?:ev|electric|vehicle|model|delivery|sales|car|cybertruck|refresh|update|record|production))', re.I)
MUSK_KEEP = re.compile(r'(\bai\b|artificial intelligence|\bagent\b|robotaxi|cybercab|\brobot\b|\bchip|semiconductor|autonomous|self-driving|\bfsd\b|political|election|trump|biden|white house|senate|congress|regulation|antitrust|lawsuit|doj|sec)', re.I)
TESLA_DROP = re.compile(r'tesla.{0,40}(?:sales|deliver|deliveries|stock|shares|price target|q[1-4]|earnings|production|gigafactory|factory|\bev\b|vehicles?|cars?|car\s|model\s|delivery|record|missed?|beat|cybertruck|update|refresh|redesign)', re.I)
TESLA_KEEP = re.compile(r'(fsd|robotaxi|cybercab|autonomous|self-driving|\bchip|semiconductor|\bai\b|artificial intelligence|\bagent\b|\brobot\b|dojo|optimus)', re.I)

# 3) Uber / Lyft 外卖业务剔除（保留自动驾驶/Robotaxi）
UBER_LYFT_DROP = re.compile(r'(uber\s+eats|ubereats|lyft\s+(?:delivery|pink|silver)|food delivery|meal delivery|delivery service|doordash|grubhub)', re.I)
UBER_LYFT_KEEP = re.compile(r'(robotaxi|autonomous|self-driving|driverless|waymo|zoox|cruise|\bav\b|self drive)', re.I)

# 4) 亚马逊：仅保留 AI/云/芯片/Agent/自动驾驶/机器人；其余（电商/广告/硬件/物流/偶发 AI 营销）剔除
#    注意：不使用裸 \bai\b（会命中 "AI 拍照亭" 等偶发 AI 营销），改用 substantive Amazon-AI 信号
AMAZON_KEEP = re.compile(r'(\bai\b|artificial intelligence|alexa ai|\baws\b|cloud|bedrock|chip|semiconductor|agent|autonomous|self-driving|robot|zoox|generative|foundation model|\bllm\b|acquisition|merger|antitrust|regulator|\bfcc\b|lawsuit|deal|\bdoj\b)', re.I)

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


def exclusion_reason(text, source, is_overseas, title=None):
    """text = 标题+摘要（用于通用低价值规则）。
    title = 原始标题（可选）；促销/影视/纯股价三类**只看标题**，
    因为摘要里常出现 discount shopping platform、movie 类比等非促销语境，会造成误剔。"""
    head = title if title is not None else text
    _supply_intel = supply_price_intel(head)
    for name, pat in EXCL:
        target = head if name in TITLE_ONLY_RULES else text
        # 「消费硬件价格/规格」针对的是消费级显卡涨价等零售话题；
        # 芯片/存储的价格变动属竞争情报，不按此条剔除。
        if name == '消费硬件价格/规格' and _supply_intel:
            continue
        if pat.search(target):
            return name
    # —— 以下三类只看标题 ——
    # 促销/折扣：标题即促销特征的才剔（摘要里的 "discount platforms" 是商业模式）
    if PROMO_PAT.search(head) and not _supply_intel:
        return '促销/折扣/导购'
    # "Big Apple" 指纽约市，不是苹果公司
    if re.search(r'big apple', head, re.I) and not re.search(r'iphone|ipad|macbook|siri|cupertino|tim cook|ternus', head, re.I):
        return 'Big Apple=纽约(非苹果公司)'
    # 苹果（水果/食材）与苹果公司同名：菜谱、果园、果汁类报道不得计入 Apple
    if re.search(r'\bapple\b', head, re.I) and APPLE_FOOD_PAT.search(head) and not APPLE_TECH_PAT.search(head):
        return '苹果(水果/食材，非公司)'
    # Apple TV+ 剧集/电影：内容业务，非硬件或 AI 竞争情报（Apple TV 4K 机顶盒除外）
    if re.search(r'\bapple\b', head, re.I) and APPLE_MEDIA_PAT.search(head) and not APPLE_TECH_PAT.search(head):
        return '苹果影视内容(Apple TV+/剧集，非硬件或AI)'
    # moonshot 登月计划：
    #   a) 有小写 moonshot（通名，指登月式构想）且无公司语境 → 剔除
    #   b) 有登月语境（NASA/moon/lunar）且非公司语境 → 剔除
    if re.search(r'(?<![A-Za-z])moonshot(?![A-Za-z])', head) and not MOONSHOT_COMPANY_PAT.search(head):
        return 'moonshot=小写通名(登月式构想，非月之暗面公司)'
    if re.search(r'\bmoonshot\b', head, re.I) and LUNAR_PAT.search(head) and not MOONSHOT_COMPANY_PAT.search(head):
        return 'moonshot=登月计划(非月之暗面公司)'
    # 纯股价波动：标题只描述股价涨跌、无实质议题 → 剔除
    if STOCK_MOVE_PAT.search(head) and not SUBSTANTIVE_PAT.search(head):
        return '纯股价波动(无实质议题)'
    # 纯政治评论（选举horse-race/民调/党派攻防）：不含商业信号时无竞争情报价值。
    # 例：「Texas Turns Blue in Rebuke of Trump, Musk and GOP」→ 剔；
    #     「Musk's SpaceX wins $X Pentagon contract」→ 含 contract/military，保留。
    if STRONG_POLITICS_PAT.search(head):
        return '政治攻防/选举结果(非产业情报)'
    if POLITICS_PAT.search(head) and not BUSINESS_SIGNAL_PAT.search(head):
        return '纯政治评论(非产业情报)'
    if 'amazon' in text and EXCL_ECOMM.search(text) and not re.search(r'\bai\b|artificial intelligence|robot|autonomous|cloud|\baws\b|chip|semiconductor|model| alexa ai', text, re.I):
        return '亚马逊电商/物流(非AI)'
    return None


def topic_gate(dom_b, dom_l, auto_b, auto_l, ovb, ovl, title_l, excerpt_l, kwkeys_l, content_l, source):
    """精细化口径：针对具体品牌/来源的话题门控，命中则返回剔除原因。
    门控同样只凭「标题」判断，不读摘要/关键词/正文——与归属判定保持同一口径。"""
    head = title_l
    # 1) 纯股价波动降噪（不限来源）：仅当标题是股价涨跌且无任何实质议题时剔除
    #    （覆盖 Benzinga "X Stock Climbs..."、Yahoo 股价快讯等；有财报/芯片/AI/监管等实质议题则保留）
    if STOCK_MOVE_PAT.search(head) and not SUBSTANTIVE_PAT.search(head):
        return '纯股价波动(无实质议题)'
    # 1b) Yahoo 专属：股价+评级类软分析（即使提到 earnings 也多为复述，仍按原口径降噪）
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
    # 6) 财报前瞻：仅剔除「海外企业」的前瞻稿；自动驾驶与国内企业的前瞻保留
    #    （Uber/小鹏等无人驾驶相关前瞻含 robotaxi 投入信息，国内企业前瞻亦作动态参考）
    if EARNINGS_PREVIEW_PAT.search(head) and not ACTUAL_EARNINGS_PAT.search(head):
        pure_overseas = bool(ovb) and not (auto_b or auto_l or dom_b or dom_l)
        if pure_overseas:
            return '财报前瞻(非实际业绩，海外企业)'
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
        # 缺列时返回空串而不是 KeyError：监测导出并非总有 content/transcript 列，
        # 直接喂原始 xlsx（未经 csv_to_delta）时曾因此整个脚本崩溃。
        i = idx.get(n)
        if i is None or i >= len(r):
            return ''
        v = r[i]
        return v if v is not None else ''

    # 仅收录 KB 媒体
    kb_wb = openpyxl.load_workbook(args.kb)
    kb_media = set(str(r[0]).strip() for r in kb_wb['媒体名称知识库'].iter_rows(min_row=2, values_only=True) if r[0])
    # 大小写索引：导出里常把 POLITICO / Tech in Asia / marketwatch 写成任意大小写，
    # 精确匹配会让它们被当成「野媒体」静默丢弃。已确认 KB 内不存在仅大小写不同的重名，可安全回退。
    kb_lower = {n.lower(): n for n in kb_media}

    def src_norm(s):
        s = s.strip()
        if s in kb_media:
            return s
        if s.endswith(' Online') and s[:-7] in kb_media:
            return s[:-7]
        # SRC_TO_KB 的目标必须是 KB 内真实存在的媒体；
        # 否则会以「未知媒体名」通过白名单闸门（曾差点把不在库的 ABC News 放进来）。
        if s in SRC_TO_KB:
            v = SRC_TO_KB[s]
            return v if v in kb_media else None
        # 大小写不敏感 + 剥 Online 后缀再试
        low = s.lower()
        if low in kb_lower:
            return kb_lower[low]
        if low.endswith(' online') and low[:-7] in kb_lower:
            return kb_lower[low[:-7]]
        for k, v in SRC_TO_KB.items():
            if k.lower() == low:
                return v if v in kb_media else None
        return None

    # 启动自检：SRC_TO_KB 里指向不存在媒体的映射直接报出来，避免静默失效
    _bad_src_map = sorted({k for k, v in SRC_TO_KB.items() if v not in kb_media})
    if _bad_src_map:
        print('WARNING: SRC_TO_KB 指向不存在的媒体（该映射不会生效）:', _bad_src_map)

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
            Chevy Bolt 车评挂到 GM Cruise。标题点名才算该品牌的报道。
            传入原始大小写标题：个别别名（如 Moonshot）需区分大小写。"""
            return match_in_text(title, compiled)

        dom_b = placed(C_DOM_B); dom_l = placed(C_DOM_L)
        auto_b = placed(C_AUTO_B); auto_l = placed(C_AUTO_L)
        ovb = placed(C_OVB); ovl = placed(C_OVL)
        # Cruise（通用汽车自动驾驶品牌）：仅标题命中且带 AV 语境，剔除旅游/影讯
        if cruise_hit(title_l):
            if 'Cruise' not in auto_b:
                auto_b.append('Cruise')

        is_overseas = bool(ovb or ovl)
        reason = exclusion_reason(excl_text, source, is_overseas, title=title)
        if not reason:
            # 传原始标题：门控内正则多为 re.I，但保留大小写便于后续加精确规则
            reason = topic_gate(dom_b, dom_l, auto_b, auto_l, ovb, ovl,
                               title, excerpt_l, kwkeys_l, content.lower(), source)
        if reason:
            continue

        placements = []
        for c in dom_b:
            placements.append(('国内企业', c))
        for c in auto_b:
            placements.append(('自动驾驶', c))
        for c in ovb:
            placements.append(('海外企业', c))
        # 领导人一律归到所属品牌下方（不再单列板块）；无法确定所属品牌才保留自身实体
        for c in dom_l:
            placements.append(leader_placement(c, '国内企业'))
        for c in auto_l:
            placements.append(leader_placement(c, '自动驾驶'))
        for c in ovl:
            placements.append(leader_placement(c, '海外企业'))
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
