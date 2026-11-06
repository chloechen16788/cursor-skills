#!/usr/bin/env python3
"""prep_final.py — 百度竞品同业日报 · 第三步：标题定唯一归属 + URL 去重 + 排序编号。

输入 curated.json，输出 final.json，并打印待翻译清单（idx | media_kb | section | entity | title）。
"""
import argparse, json, re
from collections import defaultdict, OrderedDict


def aliases_of(sec, ent):
    """实体名 → 用于标题匹配的别名（小写）。

    领导人实体的格式是「人名 (所属公司)」或「中文名/英文名 (公司)」：
    括号内是**公司归属标注，不是别名**。早先按 '/' 和括号整体切分，会把
    `Dara Khosrowshahi (Uber)` 里的 `Uber` 也变成别名，于是所有 Uber 标题都命中该领导人，
    再叠加「同位置取 min」的不稳定排序，Uber 的稿子会随机挂到人名下（实测 9 条）。
    括号只出现在领导人实体上（三个品牌表均无括号），故用括号作为领导人标记是安全的。
    """
    if '(' in ent or '（' in ent:
        # 只取括号前的人名部分
        head = re.split(r'[(（]', ent)[0]
        names = []
        for p in re.split(r'[/]', head):
            p = p.strip()
            if p and re.search(r'[A-Za-z]', p):
                names.append(p.lower())
        # 中文名（如「韩旭/Tony Han」中的韩旭）无需转小写匹配，交由 match_in_text 侧处理
        return names
    if ent == 'Cruise':
        return []  # 避免 "Tom Cruise" 等被误归并到 Cruise
    outs = []
    for p in re.split(r'[/(（（）)]', ent):
        p = p.strip()
        if p and re.search(r'[A-Za-z]', p):
            outs.append(p.lower())
    return outs


def norm_title(t):
    return re.sub(r'[^a-z0-9]+', '', t.lower())


# 事件级去重的停用词：去掉品牌名、证券代码、泛用动词，只留事件实词
EV_STOP = {
    'the', 'and', 'for', 'with', 'that', 'this', 'from', 'are', 'was', 'were', 'has', 'have',
    'will', 'its', 'his', 'her', 'not', 'but', 'you', 'can', 'how', 'why', 'what', 'who', 'out',
    'new', 'more', 'says', 'said', 'into', 'over', 'after', 'amid', 'about', 'than', 'then',
    'they', 'their', 'inc', 'nasdaq', 'nyse', 'otcmkts', 'aapl', 'googl', 'msft', 'amzn', 'nvda',
    'intc', 'meta', 'stock', 'stocks', 'shares', 'report', 'reports', 'reportedly', 'according',
    'here', 'there', 'now', 'just', 'still', 'first', 'could', 'would', 'may', 'might', 'one',
    'two', 'three', 'apple', 'google', 'alphabet', 'microsoft', 'nvidia', 'tesla', 'intel',
    'amazon', 'anthropic', 'openai', 'uber', 'lyft', 'waymo', 'zoox', 'xpeng', 'tiktok', 'tencent',
    # 人名与高频虚动词：它们几乎出现在同品牌的每条标题里，计入共享会虚高相似度
    'elon', 'musk', 'altman', 'amodei', 'huang', 'cook', 'ternus', 'khosrowshahi', 'zuckerberg',
    'nadella', 'pichai', 'jassy', 'bezos', 'wants', 'want', 'set', 'back', 'make', 'makes',
    'need', 'needs', 'take', 'takes', 'get', 'gets', 'hold', 'holds', 'keep', 'keeps', 'see',
    'sees', 'say', 'says', 'told', 'tell', 'like', 'best', 'top', 'big', 'next', 'last',
    'year', 'years', 'day', 'days', 'week', 'time', 'times', 'way', 'ways', 'thing', 'things',
    'use', 'uses', 'using', 'used', 'plan', 'plans', 'planned', 'launch', 'launches', 'launched',
    # 本公司产品名（作用等同品牌名）：同品牌每条都可能提到，不能作为同事件证据
    'claude', 'chatgpt', 'gemini', 'copilot', 'grok', 'siri', 'codex', 'gpt', 'llm', 'kimi',
}


# 词形归一化：英美拼写、数字缩写、单复数。缺了这层，
# "data center expansion" 与 "data centre expansion"、"$15bn" 与 "$15 billion" 会被当成不同事件。
EV_SYN = {'centre': 'center', 'centres': 'center', 'bn': 'billion', 'us$': 'billion',
          'dollars': 'billion', 'dollar': 'billion', 'cents': 'cent'}

# 通用技术/商业名词：出现在任何一条标题里都不足以证明「同一事件」。
# 缺这层会把 "TeraWulf gets credit backstop for Anthropic data-center project"
# 并进 "Google to invest $15bn in Malaysia's data center expansion"——只因共享 {data, center}。
EV_GENERIC = {
    'data', 'center', 'centre', 'model', 'code', 'cloud', 'chip', 'platform', 'service',
    'feature', 'update', 'launch', 'product', 'market', 'company', 'business', 'tech',
    'technology', 'app', 'user', 'customer', 'custom', 'price', 'cost', 'deal', 'sale',
    'growth', 'demand', 'supply', 'invest', 'investment', 'billion', 'million', 'fund',
    'funding', 'raise', 'offer', 'partner', 'partnership', 'global', 'world', 'industry',
}


def _canon(w):
    w = EV_SYN.get(w, w)
    if len(w) > 4 and w.endswith('ies'):
        return w[:-3] + 'y'
    if len(w) > 4 and w.endswith('es') and not w.endswith('ses'):
        return w[:-2]
    if len(w) > 3 and w.endswith('s') and not w.endswith('ss'):
        return w[:-1]
    return w


def ev_tokens(t):
    t = re.sub(r'(\d+)\s?bn\b', r'\1billion', t.lower())
    return {_canon(w) for w in re.findall(r'[a-z0-9]+', t) if len(w) >= 3 and w not in EV_STOP}


def event_dedup(items, per_event=1, rare_df=4):
    """同一事件的多家转载合并，每个事件保留最靠前的 per_event 条。

    判定（满足任一即同事件）：
      1. Jaccard >= 0.5                        —— 近乎同题（同一稿本地台分发）
      2. 共享 >= 2 个稀有实词（df <= rare_df）  —— 措辞不同但事件词一致
      3. 共享 >= 3 个实词且至少 1 个稀有        —— 各家换主语、事件词一致
      4. 共享 >= 2 个实词且至少 1 个稀有        —— 覆盖「Mamdani 指控 / Sanders 指控 / 课堂噩梦」
         这类主语各异、只共享 {accuses, school} 的同一事件报道
    判据 4 偏松，但配合 EV_STOP 剔除品牌名/人名/虚动词 + 词形归一化，实测未出现跨事件误并。
    若某批数据出现过度合并，用 --per-event 2 或调严此处。
    """
    out = []
    groups = defaultdict(list)
    for x in items:
        groups[(x['section'], x['entity'])].append(x)
    for _, its in groups.items():
        df = defaultdict(int)
        tk = {}
        for x in its:
            t = ev_tokens(x['title'])
            tk[id(x)] = t
            for w in t:
                df[w] += 1
        its = sorted(its, key=lambda y: (-y.get('pscore', 0), -y['impact']))
        clusters = []
        for x in its:
            tx = tk[id(x)]
            placed = False
            for c in clusters:
                ty = c['tok']
                if not tx or not ty:
                    continue
                shared = tx & ty
                jac = len(shared) / len(tx | ty)
                # 有效稀有词：低频 **且** 不是通用技术/商业名词。
                # 只看低频是不够的——"data"/"center" 因只出现在一小簇里反而低频，
                # 会把「TeraWulf 为 Anthropic 数据中心做信用背书」并进「谷歌投资马来西亚数据中心」。
                rare_shared = {w for w in shared if df[w] <= rare_df and w not in EV_GENERIC}
                if (jac >= 0.5
                        or len(rare_shared) >= 2
                        or (len(shared) >= 2 and rare_shared)):
                    c['items'].append(x)
                    c['tok'] = tx | ty
                    placed = True
                    break
            if not placed:
                clusters.append({'tok': set(tx), 'items': [x]})
        for c in clusters:
            out.extend(c['items'][:per_event])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True)
    ap.add_argument('--out', default='final.json')
    ap.add_argument('--event-dedup', action='store_true',
                    help='启用事件级去重：同一事件只留代表稿（默认关闭——不同媒体的同事件报道全部保留）')
    ap.add_argument('--per-event', type=int, default=1, help='配合 --event-dedup：同一事件保留几条，默认 1')
    ap.add_argument('--no-event-dedup', action='store_true', help='（已废弃，默认即为此行为）')
    args = ap.parse_args()

    final = json.load(open(args.input))

    # 1) 归属唯一化
    pairs = sorted(set((x['section'], x['entity']) for x in final))
    alias_index = []
    for sec, ent in pairs:
        for a in aliases_of(sec, ent):
            alias_index.append((a, sec, ent))
    alias_index.sort(key=lambda t: -len(t[0]))

    def title_hits(tl):
        hits = []
        for a, sec, ent in alias_index:
            m = re.search(r'(?<![a-z0-9])' + re.escape(a) + r'(?![a-z0-9])', tl)
            if m:
                hits.append((m.start(), sec, ent))
        return hits

    for x in final:
        hits = title_hits(x['title'].lower())
        if not hits:
            continue
        # 客户重点关注的 Apple Intelligence 稿：按标题中最早出现的实体归位。
        # 必须与 curation.unique_placement 的 focus 分支保持一致——否则这里的
        # 「领导人优先」会把 "Apple's Siri AI Could Become a Paid…CEO John Ternus"
        # 挪回领导人所属品牌，Apple 板块就看不到这条 AI 动态。
        if x.get('focus'):
            pick = min(hits, key=lambda h: h[0])
            x['section'], x['entity'] = pick[1], pick[2]
            continue
        if x['section'] in ('国内企业', '自动驾驶'):
            continue  # 全面收录板块：标题仍命中本板块品牌则不迁移
        pick = min(hits, key=lambda h: (h[0], h[1], h[2]))
        x['section'], x['entity'] = pick[1], pick[2]

    # 2) 全局 URL 去重
    seen_urls = set(); _deduped = []
    for x in final:
        if x['url'] in seen_urls:
            continue
        seen_urls.add(x['url']); _deduped.append(x)
    final = _deduped

    # 2b) 全局同标题去重：同一稿件被多个地方台/子站分发时 URL 不同（如 CBS 本地台），
    #     仅靠 URL 去不掉，会同一标题重复 5 次。按规范化标题保留影响力最高的一条。
    best = {}
    for x in final:
        k = norm_title(x['title'])
        if not k:
            best[id(x)] = x
            continue
        cur = best.get(k)
        if cur is None or x['impact'] > cur['impact']:
            best[k] = x
    final = list(best.values())

    # 2c) 近似重复去重：同一媒体对同一事件改标题多次发布（Bloomberg 的 "... , More - Bloomberg"
    #     行情综述、WSJ 同一选题两个标题），标题字面不同但词集高度重合。
    #     仅在「同板块 + 同实体 + 同媒体」内比较，避免误伤不同媒体对同一事件的独立报道。
    STOP = {'the', 'and', 'for', 'with', 'that', 'this', 'from', 'are', 'was', 'were',
            'has', 'have', 'will', 'its', 'his', 'her', 'not', 'but', 'you', 'can',
            'how', 'why', 'what', 'who', 'out', 'new', 'more', 'says', 'said', 'into',
            'over', 'after', 'amid', 'about', 'than', 'then', 'they', 'their'}

    def toks(t):
        return {w for w in re.findall(r'[a-z0-9]+', t.lower()) if len(w) >= 3 and w not in STOP}

    kept = []
    for x in sorted(final, key=lambda i: -i['impact']):
        tx = toks(x['title'])
        dup = False
        for y in kept:
            if (x['section'], x['entity'], x['media_kb']) != (y['section'], y['entity'], y['media_kb']):
                continue
            ty = toks(y['title'])
            if not tx or not ty:
                continue
            if len(tx & ty) / len(tx | ty) >= 0.5:
                dup = True
                break
        if not dup:
            kept.append(x)
    final = kept

    # 2d) 事件级去重：同一事件被多家媒体分别报道时（标题措辞差异大、URL/媒体都不同），
    #     前两步都抓不到，会导致「Google 关闭学校搜索」出现 12 次。
    #     按稀有实词签名归并，每个事件保留最靠前的 per_event 条。
    # 默认不做事件级去重：不同媒体对同一事件的报道各自独立，全部保留。
    # 仅当显式 --event-dedup 时才收敛为每事件 per_event 条。
    if args.event_dedup:
        final = event_dedup(final, per_event=args.per_event)

    # 3) 排序：板块顺序 -> 实体内按事件归并 -> 影响力
    SEC_ORDER = ['国内企业', '自动驾驶', '海外企业', '企业领导人']
    groups = OrderedDict()
    for sec in SEC_ORDER:
        groups[sec] = defaultdict(list)
    for x in final:
        groups[x['section']][x['entity']].append(x)

    ordered = []
    for sec in SEC_ORDER:
        ent_dict = groups[sec]
        ents = sorted(ent_dict.items(), key=lambda kv: -max(i['impact'] for i in kv[1]))
        for ent, items in ents:
            ev = defaultdict(list)
            for it in items:
                ev[norm_title(it['title'])].append(it)
            # 与第五版一致：同一规范化标题先归并。簇间、簇内都是 focus、pscore、impact。
            # 入华 0 / 其他 Apple Intelligence 1 / 普通 2。
            # 措辞不同的同事件相邻不在这里做，由 build_doc.discover_events 对全量标题聚类，
            # 再按 focus 稳定分块。不要把 pscore 放进那一层的簇排序键。
            def _frank(it):
                return {'apple_intel_cn': 0, 'apple_intel': 1}.get(it.get('focus', ''), 2)

            event_groups = sorted(
                ev.values(),
                key=lambda g: (min(_frank(i) for i in g),
                               -max(i.get('pscore', 0) for i in g),
                               -max(i['impact'] for i in g)))
            for g in event_groups:
                g.sort(key=lambda i: (_frank(i), -i.get('pscore', 0), -i['impact']))
                for it in g:
                    ordered.append(it)

    for i, x in enumerate(ordered):
        x['idx'] = i
    json.dump(ordered, open(args.out, 'w'), ensure_ascii=False, indent=1)

    print('FINAL COUNT:', len(ordered))
    print('\n===== TRANSLATION LIST (idx | media_kb | section | entity | title) =====')
    for x in ordered:
        print(f"{x['idx']:02d} | {x['media_kb']} | {x['section']} | {x['entity']} | {x['title']}")


if __name__ == '__main__':
    main()
