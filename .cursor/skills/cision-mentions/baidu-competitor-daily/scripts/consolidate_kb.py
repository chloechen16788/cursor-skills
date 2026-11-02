#!/usr/bin/env python3
# consolidate_kb.py — 整理《翻译知识库.xlsx》：媒体 / 品牌 / 领导人 三张表，严格一一对应。
import argparse, openpyxl, re

PERSON_EN = {
    'jack ma', 'joe tsai/joseph tsai', 'eddie wu', 'yongen wu', 'eric jing', 'yiming  zhang',
    'yiming zhang', 'rubo liang', 'shou zi chew', 'pony ma', 'martin lau', 'colin huang',
    'yixiao cheng/cheng yixiao', 'zhilin yang/yang zhilin', 'junjie yan', 'wenfeng liang',
    'tekedra mawakana', 'dmitri dolgov', 'aicha evans', 'alex kendall', 'dara khosrowshahi',
    'tony han', 'james peng', 'xiaopeng he', 'david risher', 'elon musk', 'musk', 'sundar pichai',
    'pichai', 'demis hassabis', 'satya nadella', 'nadella', 'mark zuckerberg', 'zuckerberg',
    'john ternus', 'tim cook', 'cook', 'andy jassy', 'matt garman', 'jeff bezos', 'jensen huang',
    'arvind krishna', 'sam altman', 'dario amodei', 'bill gates',
}

VARIANT_EN = {'yongen wu'}  # 吴泳铭变体，标准名取 Eddie Wu


def is_person(en):
    return en.lower().strip() in PERSON_EN


def read_sheet(wb, name):
    ws = wb[name]
    rows = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        en, zh = (r[0] if len(r) > 0 else None), (r[1] if len(r) > 1 else None)
        if en is None or str(en).strip() == '':
            continue
        rows.append((str(en).strip(), str(zh).strip() if zh is not None else ''))
    return rows


def dedup(rows, extras):
    seen = {}
    out = []
    for en, zh in list(rows) + extras:
        e = re.sub(r'\s+', ' ', en).strip()
        z = zh.strip()
        if e == '':
            continue
        if e.lower() in {'ai'} and z.lower() == 'ai':
            continue
        if e in seen:
            continue
        seen[e] = z
        out.append((e, z))
    return out


def check_one2one(rows, sheet):
    zh_map = {}
    conflicts = []
    for en, zh in rows:
        if zh == '':
            continue
        if zh in zh_map and zh_map[zh] != en:
            conflicts.append((zh, zh_map[zh], en))
        else:
            zh_map[zh] = en
    if conflicts:
        print(f'  [冲突] {sheet} 同一中文译名对应多个英文：')
        for c in conflicts:
            print('     ', c)
    else:
        print(f'  [OK] {sheet}：中文译名均唯一对应（{len(rows)} 条）')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True, help='待整理的知识库 xlsx')
    ap.add_argument('--out', required=True, help='输出知识库 xlsx')
    args = ap.parse_args()

    wb = openpyxl.load_workbook(args.src)
    media = read_sheet(wb, '媒体名称知识库')
    brand = read_sheet(wb, '品牌名称翻译知识库')

    brand_rows, person_rows = [], []
    for en, zh in brand:
        (person_rows if is_person(en) else brand_rows).append((en, zh))

    media_extra = [
        ('KIKK-AM Online', 'KIKK-AM 电台'),
        ('CBSNews Los Angeles', 'CBS 洛杉矶'),
        ('KOVR-TV Online', 'KOVR 电视台'),
    ]
    brand_extra = [('Cybercab', 'Cybercab')]

    media_clean = dedup(media, media_extra)
    brand_clean = dedup(brand_rows, brand_extra)
    person_clean = dedup(person_rows, [])
    person_clean = [(en, zh) for en, zh in person_clean if en.lower() not in VARIANT_EN]

    print('=== 一一对应校验 ===')
    check_one2one(media_clean, '媒体')
    check_one2one(brand_clean, '品牌')
    check_one2one(person_clean, '领导人')

    out_wb = openpyxl.Workbook()
    def write_sheet(ws, title, rows):
        ws.append(['英文', '中文'])
        for en, zh in rows:
            ws.append([en, zh])
        ws.title = title
    ws1 = out_wb.active
    write_sheet(ws1, '媒体名称知识库', media_clean)
    ws2 = out_wb.create_sheet('品牌名称翻译知识库')
    write_sheet(ws2, '品牌名称翻译知识库', brand_clean)
    ws3 = out_wb.create_sheet('领导人名称翻译知识库')
    write_sheet(ws3, '领导人名称翻译知识库', person_clean)
    out_wb.save(args.out)
    print('\n=== 写入完成 ===')
    print(f'媒体：{len(media_clean)} 条 / 品牌：{len(brand_clean)} 条 / 领导人：{len(person_clean)} 条')
    print('文件：', args.out)


if __name__ == '__main__':
    main()
