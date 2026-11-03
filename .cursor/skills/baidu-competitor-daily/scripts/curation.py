#!/usr/bin/env python3
"""curation.py — 百度竞品同业日报 · 第二步：优先级评分 + 唯一归属 + 板块限额。

输入 candidates.json + 原始 delta xlsx（用于打分所需的 excerpt/keywords/content），
输出 curated.json，并打印待翻译清单。
"""
import argparse, json, re, collections, openpyxl


def load_raw(raw_path, sheet='delta'):
    wb = openpyxl.load_workbook(raw_path, read_only=True)
    ws = wb[sheet]
    rows = list(ws.iter_rows(values_only=True))
    header = rows[0]
    idx = {h: i for i, h in enumerate(header)}
    def col(r, n):
        v = r[idx[n]]
        return v if v is not None else ''
    raw_by_url = {}
    for r in rows[1:]:
        u = str(col(r, 'url'))
        raw_by_url[u] = (str(col(r, 'excerpt')), str(col(r, 'keywords')), str(col(r, 'content'))[:1500])
    return raw_by_url


PRIORITY = {
    '监管/regulation': re.compile(r'regulat|antitrust|lawsuit|sue|sued|ban |probe|investigat|\beu\b|doj|\bftc\b|\bcma\b|ofcom|senate|congress|合规|监管', re.I),
    '芯片/chip': re.compile(r'\bchip|semiconductor|export control|export ban|\bfab\b|tsmc|\bhbm\b|ai chip|半导体|芯片', re.I),
    '中美/China-US': re.compile(r'\bchina\b|u\.s\.|us-china|beijing|tariff|chinese|中美|中国', re.I),
    '英国/UK': re.compile(r'\buk\b|britain|british|ofcom|\bcma\b|london', re.I),
    '联合国/机构预警': re.compile(r'\bun\b|united nations|oecd|iea|\bwarnings?\b|\bwarn|advocat|联合国|预警', re.I),
    '就业/employment': re.compile(r'\bjob|employ|layoff|workforce|unemployment|就业', re.I),
    '上市/IPO': re.compile(r'\bipo\b|go public|listing|\bs-1\b|上市|募股', re.I),
    '融资/funding': re.compile(r'funding|raise[sd]?\s+\\\$|valuation|series a|series b|series c|融资|募资', re.I),
    '业绩/earnings': re.compile(r'earnings|revenue|profit|quarterly|results|guidance|财报|业绩|净利', re.I),
    'Robotaxi/自动驾驶': re.compile(r'robotaxi|self-driving|autonomous|waymo|cruise|zoox|weride|pony|cybercab|无人驾驶', re.I),
    '独家/exclusive': re.compile(r'exclusive|exclusively|独家', re.I),
}


def priority_score(x, raw_by_url):
    raw = raw_by_url.get(x['url'])
    excerpt, kw, content = raw if raw else ('', '', '')
    t = (x['title'] + ' ' + kw + ' ' + excerpt + ' ' + content).lower()
    score = 0
    hits = []
    for name, pat in PRIORITY.items():
        if pat.search(t):
            score += 1
            hits.append(name)
    if x.get('ovl') or x.get('dom_l') or x.get('auto_l'):
        if re.search(r'ceo|chief|founder|president|says|said|warns|predict|view|interview|观点|表示', t):
            score += 1
            hits.append('领导人观点')
    return score, hits


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


def unique_placement(x, alias_index):
    secs = set(s for s, e in x['placements'])
    hits = []
    for a, s, e in alias_index:
        m = re.search(r'(?<![a-z0-9])' + re.escape(a) + r'(?![a-z0-9])', x['title'].lower())
        if m:
            hits.append((m.start(), s, e))
    if not hits:
        return x['placements'][0]
    if ('国内企业' in secs) or ('自动驾驶' in secs):
        da = [h for h in hits if h[1] in ('国内企业', '自动驾驶')]
        if da:
            p = min(da, key=lambda h: h[0]); return (p[1], p[2])
    leads = [h for h in hits if h[1] == '企业领导人']
    p = min(leads or hits, key=lambda h: h[0])
    return (p[1], p[2])


CAP = {'海外企业': 5, '企业领导人': 8, '国内企业': 50, '自动驾驶': 50}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--candidates', required=True)
    ap.add_argument('--raw', required=True, help='原始 delta xlsx（用于打分）')
    ap.add_argument('--sheet', default='delta')
    ap.add_argument('--out', default='curated.json')
    args = ap.parse_args()

    data = json.load(open(args.candidates))
    raw_by_url = load_raw(args.raw, args.sheet)

    for x in data:
        s, hits = priority_score(x, raw_by_url)
        x['pscore'] = s
        x['phits'] = hits

    # 唯一归属（在限额前完成）
    all_pairs = set()
    for x in data:
        for s, e in x['placements']:
            all_pairs.add((s, e))
    alias_index = []
    for s, e in all_pairs:
        for a in aliases_of(s, e):
            alias_index.append((a, s, e))
    alias_index.sort(key=lambda t: -len(t[0]))

    for x in data:
        s, e = unique_placement(x, alias_index)
        x['section'], x['entity'] = s, e

    buckets = collections.defaultdict(list)
    for x in data:
        buckets[(x['section'], x['entity'])].append(x)
    for k in buckets:
        buckets[k].sort(key=lambda x: (x['pscore'], x['impact']), reverse=True)

    selected_ids = set(); selected_list = []
    for (s, e), items in buckets.items():
        cap = CAP.get(s, 6)
        items_sorted = sorted(items, key=lambda x: (x['pscore'] > 0, x['pscore'], x['impact']), reverse=True)
        for x in items_sorted[:cap]:
            key = (x['url'], s, e)
            if key in selected_ids:
                continue
            selected_ids.add(key)
            selected_list.append({'url': x['url'], 'title': x['title'], 'source': x['source'],
                                  'media_kb': x.get('media_kb', x['source']),
                                  'country': x['country'], 'lang': x['lang'], 'pub': x['pub'],
                                  'impact': x['impact'], 'pscore': x['pscore'], 'phits': x['phits'],
                                  'section': s, 'entity': e})

    json.dump(selected_list, open(args.out, 'w'), ensure_ascii=False, indent=1)
    bysec = collections.Counter(x['section'] for x in selected_list)
    print('SELECTED COUNT:', len(selected_list))
    print('By section:', dict(bysec))
    byent = collections.Counter((x['section'], x['entity']) for x in selected_list)
    for (s, e), c in sorted(byent.items()):
        print(f'  [{s}] {e}: {c}')
    print('\n========= TRANSLATION LIST =========')
    for x in sorted(selected_list, key=lambda y: (y['section'], -y['impact'])):
        print(f"[{x['section']}|{x['entity']}|{x['source']}|imp{x['impact']:.0f}|p{x['pscore']}] {x['title']}")
    print('\nSaved ->', args.out)


if __name__ == '__main__':
    main()
