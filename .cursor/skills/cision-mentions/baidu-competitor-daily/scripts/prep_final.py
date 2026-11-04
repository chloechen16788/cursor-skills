#!/usr/bin/env python3
"""prep_final.py — 百度竞品同业日报 · 第三步：标题定唯一归属 + URL 去重 + 排序编号。

输入 curated.json，输出 final.json，并打印待翻译清单（idx | media_kb | section | entity | title）。
"""
import argparse, json, re
from collections import defaultdict, OrderedDict


def aliases_of(sec, ent):
    if sec == '企业领导人':
        name = ent.split('(')[0].strip()
        return [name.lower()] if re.search(r'[A-Za-z]', name) else []
    if ent == 'Cruise':
        return []  # 避免 "Tom Cruise" 等被误归并到 Cruise
    outs = []
    for p in re.split(r'[/((（）)]', ent):
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
}


def ev_tokens(t):
    return {w for w in re.findall(r'[a-z0-9]+', t.lower()) if len(w) >= 3 and w not in EV_STOP}


def event_dedup(items, per_event=1, rare_df=4):
    """同一事件的多家转载合并，每个事件保留最靠前的 per_event 条。

    判定：同板块+同实体内，若两条标题 Jaccard>=0.5，或共享 >=2 个「稀有实词」
    （该品牌候选内出现次数 <= rare_df），视为同一事件。
    稀有词签名能让「Apple warns memory prices...」与「Apple forecasts margin drop
    as rising memory costs bite」归并，同时不误合「Siri 开放给开发者」与「AI 代理风险」。
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
                jac = len(tx & ty) / len(tx | ty)
                rare_shared = {w for w in (tx & ty) if df[w] <= rare_df}
                if jac >= 0.5 or len(rare_shared) >= 2:
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
    ap.add_argument('--per-event', type=int, default=1, help='同一事件保留几条代表稿，默认 1')
    ap.add_argument('--no-event-dedup', action='store_true', help='关闭事件级去重（保留全部同事件稿）')
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
        if x['section'] in ('国内企业', '自动驾驶'):
            continue  # 全面收录板块：标题仍命中本板块品牌则不迁移
        leads = [h for h in hits if h[1] == '企业领导人']
        pick = min(leads or hits, key=lambda h: h[0])
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
    if not args.no_event_dedup:
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
            event_groups = sorted(ev.values(), key=lambda g: (-max(i.get('pscore', 0) for i in g), -max(i['impact'] for i in g)))
            for g in event_groups:
                g.sort(key=lambda i: (-i.get('pscore', 0), -i['impact']))
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
