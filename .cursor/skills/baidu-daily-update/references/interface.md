# 处理模块交给父技能的接口

维护时保持下表。父技能的 `publish_daily_report.py` 不用改参数。

| 步骤 | 脚本 | 必保留参数 | 产物 |
| --- | --- | --- | --- |
| 1 | `filter3.py` | `--input` `--kb` `--out`（`--drops` 可选，定时命令不传） | `candidates.json` |
| 2 | `curation.py` | `--candidates` `--raw` `--out` | `curated.json` |
| 3 | `prep_final.py` | `--input` `--out` | `final.json` |
| 4 | `make_zh_template.py` | `--final` `--out` | `zh_template.json` |
| 5 | 按标题填写 | — | `zh.json` |

`final.json` 条目字段：`idx`、`section`、`entity`、`title`、`url`、`media_kb`、`impact`。

`section` 只使用：`国内企业`、`自动驾驶`、`海外企业`、`企业领导人`。

`zh.json`：与 `final.json` 等长，按 `idx` 有非空 `zh`。

知识库工作表名：`媒体名称知识库`、`品牌名称翻译知识库`、`领导人名称翻译知识库`。
