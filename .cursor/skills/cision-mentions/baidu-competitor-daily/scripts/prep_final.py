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
    outs = []
    for p in re.split(r'[/((（）)]', ent):
        p = p.strip()
        if p and re.search(r'[A-Za-z]', p):
            outs.append(p.lower())
    return outs


def norm_title(t):
    return re.sub(r'[^a-z0-9]+', '', t.lower())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True)
    ap.add_argument('--out', default='final.json')
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
            event_groups = sorted(ev.values(), key=lambda g: -max(i['impact'] for i in g))
            for g in event_groups:
                g.sort(key=lambda i: -i['impact'])
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
