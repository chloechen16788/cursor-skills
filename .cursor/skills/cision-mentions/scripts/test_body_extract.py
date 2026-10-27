#!/usr/bin/env python3
"""正文清洗交给模型。单测可以替模型回一段记录好的回复，不检查正则裁切。"""

from __future__ import annotations

import json
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
RECORDED = json.dumps(
    {
        "title": "Harbor City port reopens after the storm",
        "body": "The harbor master said the port reopened at dawn after crews cleared the last debris.",
    }
)
AFTER = "2026-10-24T23:00:00.000Z"


class BodyExtractTest(unittest.TestCase):
    def test_model_reply_becomes_title_and_body(self) -> None:
        seen: list[str] = []

        def complete(prompt: str) -> str:
            seen.append(prompt)
            return RECORDED

        cleaned = body_extract.clean_markdown(MESSY, complete)
        self.assertEqual(len(seen), 1)
        self.assertIn(MESSY, seen[0])
        self.assertIn(
            "Drop navigation, ads, related links, and markdown link syntax.", seen[0]
        )
        self.assertEqual(cleaned["title"], "Harbor City port reopens after the storm")
        self.assertEqual(
            cleaned["body"],
            "The harbor master said the port reopened at dawn after crews cleared the last debris.",
        )
        self.assertEqual(cleaned["body"], json.loads(RECORDED)["body"])

    def test_model_text_is_stored_without_further_cleaning(self) -> None:
        reply = '{"title": "Final", "body": "The score was 3-2 [in overtime]."}'

        cleaned = body_extract.clean_markdown("messy page", lambda prompt: reply)
        self.assertEqual(cleaned["title"], "Final")
        self.assertEqual(cleaned["body"], "The score was 3-2 [in overtime].")

    def test_failed_url_still_writes_and_sends_link(self) -> None:
        calls: list[str] = []
        sent: list[str] = []

        class Fake:
            def prepare(self) -> None:
                calls.append("prepare")

            def replace_all(self, rows: list[dict]) -> tuple[int, int]:
                calls.append("replace")
                self.rows = rows
                return 5, len(rows)

        def scrape(urls: list[str]) -> dict:
            calls.append("scrape")
            self.assertEqual(
                urls, ["https://news.example/good", "https://news.example/bad"]
            )
            return {
                "https://news.example/good": {"markdown": MESSY, "error": ""},
                "https://news.example/bad": {"markdown": "", "error": "HTTP 403"},
            }

        def complete(prompt: str) -> str:
            self.assertIn("Harbor City port reopens", prompt)
            return RECORDED

        fake = Fake()
        summary = body_extract.run_bodies(
            header=["id", "url", "title"],
            rows=[
                ["1", "https://news.example/good", "csv good"],
                ["2", "https://news.example/bad", "csv bad"],
                ["3", "https://news.example/good", "duplicate"],
            ],
            after=AFTER,
            scrape=scrape,
            complete=complete,
            client=fake,
            send=sent.append,
            secrets_ok=True,
        )
        self.assertEqual(calls, ["scrape", "prepare", "replace"])
        self.assertEqual(len(fake.rows), 2)
        self.assertEqual(
            fake.rows[0]["标题"], "Harbor City port reopens after the storm"
        )
        self.assertEqual(fake.rows[0]["正文"], json.loads(RECORDED)["body"])
        self.assertEqual(fake.rows[0]["错误"], "")
        self.assertEqual(fake.rows[1]["id"], "2")
        self.assertEqual(fake.rows[1]["正文"], "")
        self.assertEqual(fake.rows[1]["标题"], "csv bad")
        self.assertEqual(fake.rows[1]["错误"], "HTTP 403")
        self.assertEqual(sent, ["2026-10-25\n" + body_extract.DAILY_WIKI_URL])
        self.assertIn("table=tblRwSj33U1e4t4N", sent[0])
        self.assertIn("view=vew0Gce8xU", sent[0])
        self.assertNotIn(".csv", sent[0])
        self.assertEqual(summary["feishu"], "sent")
        self.assertEqual(summary["delta_rows"], 3)
        self.assertEqual(summary["unique_urls"], 2)
        self.assertEqual(summary["bitable_deleted"], 5)
        self.assertEqual(summary["bitable_written"], 2)
        self.assertEqual(summary["data_date"], "2026-10-25")

    def test_zero_delta_skips_scrape_and_message(self) -> None:
        def scrape(urls: list[str]) -> dict:
            raise AssertionError("增量为 0 时不应抓取")

        def send(text: str) -> None:
            raise AssertionError("增量为 0 时不应发第二条消息")

        class Fake:
            def prepare(self) -> None:
                raise AssertionError("不应访问飞书")

            def replace_all(self, rows: list[dict]) -> tuple[int, int]:
                raise AssertionError("不应删除")

        summary = body_extract.run_bodies(
            header=["id", "url"],
            rows=[],
            after=AFTER,
            scrape=scrape,
            complete=lambda prompt: RECORDED,
            client=Fake(),
            send=send,
            secrets_ok=False,
            secret_error=body_extract.missing_firecrawl_message(),
        )
        self.assertEqual(summary["bodies"], "skipped")
        self.assertEqual(summary["feishu"], "skipped")
        self.assertEqual(
            body_extract.format_body_summary(summary),
            "delta_rows=0\nbodies=skipped\nfeishu=skipped",
        )

    def test_missing_firecrawl_key_stops_before_delete(self) -> None:
        def scrape(urls: list[str]) -> dict:
            raise AssertionError("缺密钥时不应抓取")

        class Fake:
            def prepare(self) -> None:
                raise AssertionError("不应访问飞书")

            def replace_all(self, rows: list[dict]) -> tuple[int, int]:
                raise AssertionError("不应删除")

        with self.assertRaises(RuntimeError) as caught:
            body_extract.run_bodies(
                header=["id", "url"],
                rows=[["1", "https://news.example/a"]],
                after=AFTER,
                scrape=scrape,
                complete=lambda prompt: RECORDED,
                client=Fake(),
                send=lambda text: None,
                secrets_ok=False,
                secret_error=body_extract.missing_firecrawl_message(),
            )
        self.assertIn("FIRECRAWL_API_KEY", str(caught.exception))
        self.assertIn("未删除", str(caught.exception))

    def test_prepare_failure_does_not_delete_or_send(self) -> None:
        sent: list[str] = []

        class Fake:
            def prepare(self) -> None:
                raise RuntimeError("字段 403")

            def replace_all(self, rows: list[dict]) -> tuple[int, int]:
                raise AssertionError("不应删除")

        with self.assertRaises(RuntimeError) as caught:
            body_extract.run_bodies(
                header=["id", "url"],
                rows=[["1", "https://news.example/a"]],
                after=AFTER,
                scrape=lambda urls: {urls[0]: {"markdown": MESSY, "error": ""}},
                complete=lambda prompt: RECORDED,
                client=Fake(),
                send=sent.append,
                secrets_ok=True,
            )
        self.assertIn("未删除", str(caught.exception))
        self.assertEqual(sent, [])

    def test_write_failure_does_not_send(self) -> None:
        sent: list[str] = []

        class Fake:
            def prepare(self) -> None:
                return None

            def replace_all(self, rows: list[dict]) -> tuple[int, int]:
                raise RuntimeError("写入 500")

        with self.assertRaises(RuntimeError) as caught:
            body_extract.run_bodies(
                header=["id", "url"],
                rows=[["1", "https://news.example/a"]],
                after=AFTER,
                scrape=lambda urls: {urls[0]: {"markdown": MESSY, "error": ""}},
                complete=lambda prompt: RECORDED,
                client=Fake(),
                send=sent.append,
                secrets_ok=True,
            )
        self.assertIn("未发送群链接", str(caught.exception))
        self.assertEqual(sent, [])

    def test_bitable_url_uses_obj_token(self) -> None:
        calls: list[tuple[str, str, dict | None]] = []

        def request(
            url: str, method: str, payload: dict | None = None, token: str | None = None
        ) -> dict:
            calls.append((method, url, payload))
            self.assertEqual(token, "tenant")
            if "get_node" in url:
                self.assertIn("token=" + body_extract.WIKI_NODE_TOKEN, url)
                return {
                    "data": {"node": {"obj_type": "bitable", "obj_token": "APP_REAL"}}
                }
            if method == "GET" and "/fields" in url:
                return {"data": {"items": [{"field_name": "文本"}], "has_more": False}}
            if method == "POST" and url.endswith("/fields"):
                return {"data": {}}
            if method == "GET" and "/records?" in url:
                return {
                    "data": {"items": [{"record_id": "rec_old"}], "has_more": False}
                }
            if "batch_delete" in url:
                return {"data": {}}
            if "batch_create" in url:
                return {"data": {}}
            raise AssertionError((method, url))

        table = body_extract.DailyTable(request=request, token="tenant")
        table.prepare()
        deleted, written = table.replace_all(
            [
                {
                    "id": "1",
                    "url": "https://news.example/a",
                    "标题": "t",
                    "正文": "b",
                    "错误": "",
                }
            ]
        )
        self.assertEqual((deleted, written), (1, 1))
        bitable = [url for method, url, payload in calls if "/bitable/" in url]
        self.assertTrue(bitable)
        for url in bitable:
            self.assertIn("/apps/APP_REAL/", url)
            self.assertNotIn("/apps/" + body_extract.WIKI_NODE_TOKEN, url)
        self.assertFalse(any(method == "PUT" for method, url, payload in calls))
        deleted_payloads = [
            payload
            for method, url, payload in calls
            if url.endswith("/records/batch_delete")
        ]
        self.assertEqual(deleted_payloads, [{"records": ["rec_old"]}])
        created = [payload for method, url, payload in calls if "batch_create" in url][
            0
        ]
        self.assertEqual(created["records"][0]["fields"]["正文"], "b")
        self.assertEqual(
            [
                payload["field_name"]
                for method, url, payload in calls
                if method == "POST" and url.endswith("/fields")
            ],
            list(body_extract.FIELD_NAMES),
        )

    def test_data_date_and_delta_path(self) -> None:
        self.assertEqual(body_extract.shanghai_data_date(AFTER), "2026-10-25")
        import cision_lib

        folder = f"{cision_lib.compact_stamp(AFTER)}_{cision_lib.compact_stamp('2026-10-25T23:00:00.000Z')}"
        self.assertEqual(
            body_extract.after_from_delta_path(Path("/tmp") / folder / "delta.csv"),
            AFTER,
        )

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
        self.assertIn("extract_bodies.py", skill)
        self.assertIn("一个自动化里放两条 cron 时，只会触发第一条", skill)
        self.assertIn("`0 23 * * *`", skill)
        self.assertIn("`30 10 * * *`", skill)
        self.assertIn("FIRECRAWL_API_KEY", skill)
        self.assertIn("MbglbIcF6aKwyXsCW7QcSTbIncb", skill)
        self.assertIn("vew0Gce8xU", skill)
        self.assertIn("delta_rows", skill)
        self.assertNotIn("extract_bodies", export_source)
        self.assertNotIn("import re", source)
        self.assertNotIn('"PUT"', source)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(BodyExtractTest)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
