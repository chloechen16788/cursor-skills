#!/usr/bin/env python3
"""正文追加到增量 CSV。标题用 CSV，不交给模型改写，也不写当日表。"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import body_extract

SCRIPTS = Path(__file__).resolve().parent
MESSY = """[Skip to content](https://news.example/story#content)

[Home](https://news.example/) | [Markets](https://news.example/markets)

# Advertisement

[Sponsored: Open an account](https://ads.example/open)

# Harbor City port reopens after the storm

The harbor master said the port reopened at dawn after crews cleared the last debris.

[Related: Storm timeline](https://news.example/timeline)

## More stories

- [Markets rally](https://news.example/rally)
"""
AFTER = "2026-10-24T23:00:00.000Z"


class BodyExtractTest(unittest.TestCase):
    def test_csv_title_and_full_markdown_are_stored(self) -> None:
        record = body_extract.build_record(
            {
                "id": "1",
                "url": "https://news.example/good",
                "csv_title": "CSV title stays",
            },
            {"markdown": MESSY, "error": ""},
        )
        self.assertEqual(record["标题"], "CSV title stays")
        self.assertEqual(record["content"], MESSY)
        self.assertIn(
            "[Skip to content](https://news.example/story#content)", record["content"]
        )
        self.assertIn("# Advertisement", record["content"])
        self.assertEqual(record["错误"], "")

    def test_markdown_is_not_rewritten_or_truncated(self) -> None:
        markdown = "The score was 3-2 [in overtime].\n\n[Related](https://news.example/x)"
        record = body_extract.build_record(
            {"id": "1", "url": "https://news.example/a", "csv_title": "Final"},
            {"markdown": markdown, "error": ""},
        )
        self.assertEqual(record["标题"], "Final")
        self.assertEqual(record["content"], markdown)
        long_markdown = "段" * 100001
        long_record = body_extract.build_record(
            {"id": "2", "url": "https://news.example/b", "csv_title": "Long"},
            {"markdown": long_markdown, "error": ""},
        )
        self.assertEqual(len(long_record["content"]), 100001)
        self.assertEqual(long_record["content"], long_markdown)
        with tempfile.TemporaryDirectory(prefix="cision-bodies-") as temporary:
            book = Path(temporary) / "long.xlsx"
            truncated = body_extract.write_bodies_xlsx(
                book,
                ["id", "url", "title"],
                [["9", "https://news.example/b", "Long"]],
                [long_markdown],
            )
            _, stored_rows = body_extract.read_bodies_xlsx(book)
        self.assertEqual(len(stored_rows[0][-1]), body_extract.EXCEL_CELL_LIMIT)
        self.assertEqual(truncated[0]["row"], 1)
        self.assertEqual(truncated[0]["id"], "9")
        self.assertEqual(truncated[0]["original"], 100001)
        self.assertEqual(truncated[0]["stored"], body_extract.EXCEL_CELL_LIMIT)

    def test_csv_roundtrip_keeps_title_and_full_markdown(self) -> None:
        sent: list[tuple[str, Path]] = []
        header = ["id", "url", "title"]
        rows = [
            ["1", "https://news.example/good", "csv good, still"],
            ["2", "https://news.example/bad", 'csv "bad"'],
            ["3", "https://news.example/good", "duplicate"],
        ]

        def scrape(urls: list[str]) -> dict:
            self.assertEqual(
                urls, ["https://news.example/good", "https://news.example/bad"]
            )
            return {
                "https://news.example/good": {"markdown": MESSY, "error": ""},
                "https://news.example/bad": {"markdown": "", "error": "HTTP 403"},
            }

        with tempfile.TemporaryDirectory(prefix="cision-bodies-") as temporary:
            dest = Path(temporary) / "delta-bodies.xlsx"
            summary = body_extract.run_bodies(
                header=header,
                rows=rows,
                after=AFTER,
                scrape=scrape,
                send=lambda text, path: sent.append((text, path)),
                dest=dest,
                secrets_ok=True,
            )
            out_header, out_rows = body_extract.read_bodies_xlsx(dest)
        self.assertEqual(out_header, ["id", "url", "title", "content"])
        self.assertEqual(len(out_rows), 3)
        self.assertEqual(out_rows[0][2], "csv good, still")
        self.assertEqual(out_rows[0][3], MESSY)
        self.assertEqual(out_rows[1][2], 'csv "bad"')
        self.assertEqual(out_rows[1][3], "")
        self.assertEqual(out_rows[2][2], "duplicate")
        self.assertEqual(out_rows[2][3], MESSY)
        self.assertEqual(len(sent), 1)
        notice, sent_path = sent[0]
        self.assertEqual(sent_path, dest)
        self.assertIn("data_date=2026-10-25", notice)
        self.assertIn("delta_rows=3", notice)
        self.assertIn("fetched=2", notice)
        self.assertIn("failed=1", notice)
        self.assertNotIn("csv good", notice)
        self.assertEqual(summary["feishu"], "sent")
        self.assertEqual(summary["delta_rows"], 3)
        self.assertEqual(summary["body_rows"], 3)
        self.assertEqual(summary["unique_urls"], 2)
        self.assertEqual(summary["stored_ok"], 2)
        self.assertEqual(summary["scraped_failed"], 1)
        self.assertEqual(summary["data_date"], "2026-10-25")
        self.assertTrue(str(summary["body_xlsx"]).endswith("delta-bodies.xlsx"))
        self.assertEqual(summary["truncated"], [])
        self.assertNotIn("bitable", summary)

    def test_zero_delta_skips_scrape_and_message(self) -> None:
        def scrape(urls: list[str]) -> dict:
            raise AssertionError("增量为 0 时不应抓取")

        def send(text: str, path: Path) -> None:
            raise AssertionError("增量为 0 时不应发文件")

        summary = body_extract.run_bodies(
            header=["id", "url"],
            rows=[],
            after=AFTER,
            scrape=scrape,
            send=send,
            dest=Path("/tmp/unused-bodies.csv"),
            secrets_ok=False,
            secret_error=body_extract.missing_firecrawl_message(),
        )
        self.assertEqual(summary["bodies"], "skipped")
        self.assertEqual(summary["feishu"], "skipped")
        self.assertEqual(
            body_extract.format_body_summary(summary),
            "delta_rows=0\nbodies=skipped\nfeishu=skipped",
        )

    def test_missing_firecrawl_key_stops_before_send(self) -> None:
        def scrape(urls: list[str]) -> dict:
            raise AssertionError("缺密钥时不应抓取")

        def send(text: str, path: Path) -> None:
            raise AssertionError("缺密钥时不应发送")

        with self.assertRaises(RuntimeError) as caught:
            body_extract.run_bodies(
                header=["id", "url"],
                rows=[["1", "https://news.example/a"]],
                after=AFTER,
                scrape=scrape,
                send=send,
                dest=Path("/tmp/unused-bodies.csv"),
                secrets_ok=False,
                secret_error=body_extract.missing_firecrawl_message(),
            )
        self.assertIn("FIRECRAWL_API_KEY", str(caught.exception))
        self.assertIn("没有改当日表", str(caught.exception))

    def test_write_failure_does_not_send(self) -> None:
        sent: list[tuple[str, Path]] = []

        def scrape(urls: list[str]) -> dict:
            return {urls[0]: {"markdown": MESSY, "error": ""}}

        with tempfile.TemporaryDirectory(prefix="cision-bodies-") as temporary:
            blocked = Path(temporary) / "not-a-directory"
            blocked.write_text("x", encoding="utf-8")
            dest = blocked / "delta-bodies.xlsx"
            with self.assertRaises(RuntimeError) as caught:
                body_extract.run_bodies(
                    header=["id", "url", "title"],
                    rows=[["1", "https://news.example/a", "t"]],
                    after=AFTER,
                    scrape=scrape,
                    send=lambda text, path: sent.append((text, path)),
                    dest=dest,
                    secrets_ok=True,
                )
        self.assertIn("未发送", str(caught.exception))
        self.assertEqual(sent, [])

    def test_send_failure_keeps_the_file(self) -> None:
        def scrape(urls: list[str]) -> dict:
            return {urls[0]: {"markdown": MESSY, "error": ""}}

        def send(text: str, path: Path) -> None:
            raise RuntimeError("上传 500")

        with tempfile.TemporaryDirectory(prefix="cision-bodies-") as temporary:
            dest = Path(temporary) / "delta-bodies.xlsx"
            with self.assertRaises(RuntimeError) as caught:
                body_extract.run_bodies(
                    header=["id", "url", "title"],
                    rows=[["1", "https://news.example/a", "t"]],
                    after=AFTER,
                    scrape=scrape,
                    send=send,
                    dest=dest,
                    secrets_ok=True,
                )
            self.assertTrue(dest.is_file())
            header, rows = body_extract.read_bodies_xlsx(dest)
        self.assertEqual(header[-1], "content")
        self.assertEqual(rows[0][-1], MESSY)
        self.assertIn("群消息发送失败", str(caught.exception))
        self.assertIn(str(dest), str(caught.exception))

    def test_data_date_and_delta_path(self) -> None:
        self.assertEqual(body_extract.shanghai_data_date(AFTER), "2026-10-25")
        import cision_lib

        folder = (
            f"{cision_lib.compact_stamp(AFTER)}_"
            f"{cision_lib.compact_stamp('2026-10-25T23:00:00.000Z')}"
        )
        delta = Path("/tmp") / folder / "delta.csv"
        self.assertEqual(body_extract.after_from_delta_path(delta), AFTER)
        self.assertEqual(body_extract.bodies_xlsx_path(delta).name, "delta-bodies.xlsx")

    def test_scrape_uses_only_main_content_and_not_api_key_flag(self) -> None:
        import body_extract as module

        calls: list[list[str]] = []

        def fake_run(argv, **kwargs):
            calls.append(list(argv))
            dest = Path(argv[argv.index("-o") + 1])
            dest.write_text("# Title\n\nBody\n", encoding="utf-8")

            class Proc:
                returncode = 0
                stdout = ""
                stderr = ""

            return Proc()

        original = module.subprocess.run
        module.subprocess.run = fake_run
        try:
            with tempfile.TemporaryDirectory(prefix="cision-bodies-") as temporary:
                result = module.scrape_urls(
                    ["https://example.com/a"], Path(temporary), workers=1
                )
        finally:
            module.subprocess.run = original
        self.assertEqual(calls[0][:3], ["firecrawl", "scrape", "--only-main-content"])
        self.assertNotIn("--api-key", calls[0])
        self.assertEqual(result["https://example.com/a"]["error"], "")
        self.assertIn("# Title", result["https://example.com/a"]["markdown"])

    def test_skill_runs_both_steps_in_each_automation(self) -> None:
        skill = (SCRIPTS.parent / "SKILL.md").read_text(encoding="utf-8")
        export_source = (SCRIPTS / "export_mentions.py").read_text(encoding="utf-8")
        source = (SCRIPTS / "body_extract.py").read_text(encoding="utf-8")
        push_source = (SCRIPTS / "feishu_push.py").read_text(encoding="utf-8")
        self.assertIn("extract_bodies.py", skill)
        self.assertIn("一个自动化里放两条 cron 时，只会触发第一条", skill)
        self.assertIn("`0 23 * * *`", skill)
        self.assertIn("`30 10 * * *`", skill)
        self.assertIn("FIRECRAWL_API_KEY", skill)
        self.assertIn("MbglbIcF6aKwyXsCW7QcSTbIncb", skill)
        self.assertIn("vew0Gce8xU", skill)
        self.assertIn("delta_rows", skill)
        self.assertIn("delta-bodies.xlsx", skill)
        self.assertIn("不要把正文写进当日表", skill)
        self.assertIn("整段 markdown", skill)
        self.assertIn("标题", skill)
        self.assertNotIn("extract_bodies", export_source)
        self.assertNotIn("import re", source)
        self.assertNotIn('"PUT"', source)
        self.assertNotIn("chat/completions", source)
        self.assertNotIn("jina", source.lower())
        self.assertNotIn("ARTICLE_MODEL", skill)
        self.assertNotIn("DailyTable", source)
        self.assertNotIn("batch_delete", source)
        self.assertNotIn("tblRwSj33U1e4t4N", source)
        self.assertNotIn("bitable", source)
        self.assertIn("def send_body_update", push_source)
        self.assertIn("content", skill)
        self.assertNotIn("BODY_COLUMN = \"正文\"", source)
        self.assertIn("oc_27040b0dc3a733ab164199154c489fad", push_source)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(BodyExtractTest)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
