---
name: baidu-daily-update
description: >
  外部维护人员更新「百度海外舆情日报」处理模块时使用。只在对方要求修改筛选、策展、翻译规则或《翻译知识库》时读取。
  触发说法包括「更新日报处理模块」「改筛选口径」「改策展限额」「改译名」「baidu-daily-update」。
  定时任务、提示词 run the cision mentions skill、导出 mentions、抓正文、发布飞书文档都不使用本技能。
  本技能不参与定时流水线，也不改 cision-mentions 的衔接。
---

# 更新日报处理模块

给外部维护人员用。只说明怎么改「日报处理模块」。定时任务不调用本技能。

上海 07:00 与 18:30 的自动化，以及提示词 `run the cision mentions skill`，仍然只走 `.cursor/skills/cision-mentions/SKILL.md`：同一次运行里从拉取做到发布飞书文档。不要把处理步骤拆成另一个定时任务，也不要让那条流水线改来调用本技能。

## 什么时候用

对方要改筛选口径、策展限额、翻译规则，或《翻译知识库》里的媒体、品牌、领导人译名。

## 什么时候不用

- 跑定时、导出监测流、抓正文、写飞书文档、发群消息。
- 提示词是 `run the cision mentions skill`。
- 对方要改数据源、导出顺序、文档节点或 cron。

这些都留在 `cision-mentions`。本技能不执行它们。

## 禁止改

下面这些保持现状。不要改对应脚本、文档段落、命令参数或配置。

1. **接入数据源。** stream 只接 `1023128`。不要改导出命令、多维表格、群，也不要改密钥的变量名或取值。不要把密钥写进文件、命令行或对话。
2. **导出和抓正文的顺序。** 同一次运行先 `export_mentions.py`，再 `extract_bodies.py`。`delta_rows` 为 0 就停：不抓正文，不改文档。
3. **飞书文档产出。** 仍由 `cision-mentions/scripts/publish_daily_report.py` 清空并重写 wiki 节点 `PP88weeBdi1Pcgkmpxbc48lSn5e`。保留必传参数 `--after` 和 `--raw-count`。`--after` 仍是导出标准输出里的 `after`，`--raw-count` 仍是 `delta_rows`。
4. **定时时间。** 上海 07:00 仍是 `0 23 * * *`，上海 18:30 仍是 `30 10 * * *`。两套自动化分开，提示词仍是 `run the cision mentions skill`。

不要改 `.cursor/skills/cision-mentions/SKILL.md` 的衔接行为，也不要改 `publish_daily_report.py`。

## 允许改

只改处理模块 `.cursor/skills/cision-mentions/baidu-competitor-daily/` 里的这些文件：

- `scripts/filter3.py`
- `scripts/curation.py`
- `scripts/prep_final.py`
- `scripts/make_zh_template.py`
- `references/filtering_criteria.md`
- `assets/翻译知识库.xlsx`
- 对应的筛选、策展、翻译说明：该目录 `SKILL.md` 里这三块规则，以及 `references/workflow.md`、`references/pitfalls.md` 里描述筛选、策展、翻译的段落

`consolidate_kb.py` 只用来整理知识库，不要改这个脚本。

## 更新时必须保持的顺序和产物

父技能按这个顺序调用，产物文件名不变，这样 `publish_daily_report.py` 不用改参数：

```bash
python3 .cursor/skills/cision-mentions/baidu-competitor-daily/scripts/filter3.py \
  --input <delta-bodies.xlsx> \
  --kb .cursor/skills/cision-mentions/baidu-competitor-daily/assets/翻译知识库.xlsx \
  --out <run>/candidates.json
python3 .cursor/skills/cision-mentions/baidu-competitor-daily/scripts/curation.py \
  --candidates <run>/candidates.json \
  --raw <delta-bodies.xlsx> \
  --out <run>/curated.json
python3 .cursor/skills/cision-mentions/baidu-competitor-daily/scripts/prep_final.py \
  --input <run>/curated.json \
  --out <run>/final.json
python3 .cursor/skills/cision-mentions/baidu-competitor-daily/scripts/make_zh_template.py \
  --final <run>/final.json \
  --out <run>/zh_template.json
```

然后只按标题把 `zh_template.json` 填成 `<run>/zh.json`。`len(zh) == len(final)`。不要读正文，也不要打印正文。

发布仍是父技能原有命令，参数不要增删：

```bash
python3 .cursor/skills/cision-mentions/scripts/publish_daily_report.py \
  --final <run>/final.json \
  --zh <run>/zh.json \
  --after <after> \
  --raw-count <delta_rows>
```

`final.json` 每条仍要有 `idx`、`section`、`entity`、`title`、`url`、`media_kb`、`impact`。四个 `section` 名称保持 `国内企业`、`自动驾驶`、`海外企业`、`企业领导人`。`zh.json` 按 `idx` 提供 `zh`。知识库三个表名保持「媒体名称知识库」「品牌名称翻译知识库」「领导人名称翻译知识库」。这些字段和表名是发布脚本已经在读的，改掉就要改发布脚本。

参数和字段的短表在 `references/interface.md`。

## 怎么改

1. 筛选口径先写进 `references/filtering_criteria.md`，再同步到 `scripts/filter3.py`。两边的别名表和剔除规则保持一致。
2. 策展限额和归属顺序改 `scripts/curation.py`，并改 `SKILL.md` 与 `references/pitfalls.md` 里对应的说明。先按标题做唯一归属，再套限额。
3. 标题定归属、URL 去重和 `idx` 编号留在 `prep_final.py`。`idx` 顺序就是报告顺序。
4. `make_zh_template.py` 仍从 `final.json` 生成带空 `zh` 的 `zh_template.json`。翻译只填标题。媒体、品牌、领导人译名与《翻译知识库》一一对应。
5. 译名改 `assets/翻译知识库.xlsx`。需要整理时，用现有的 `scripts/consolidate_kb.py` 做一一对应校验，不要改脚本本身。
6. 改完只核对处理模块：命令行参数、产物文件名、`final.json` / `zh.json` 字段仍能被上面的发布命令直接使用。不要为了这次修改去改父技能、导出脚本或发布脚本。
