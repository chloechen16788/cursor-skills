#!/usr/bin/env python3
"""窗口、编码、分页和去重文件规则的本地测试。不访问网络。"""

from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import cision_lib

SHANGHAI = timezone(timedelta(hours=8))


def page(header: str, *rows: str) -> str:
    lines = [header, *rows]
    return "\n".join(lines) + "\n"


class CisionMentionsTest(unittest.TestCase):
    def test_afternoon_window_matches_documented_instants(self) -> None:
        now = datetime(2026, 10, 26, 15, 0, tzinfo=SHANGHAI)
        after, before = cision_lib.shanghai_window(now)
        self.assertEqual(after, "2026-10-24T23:00:00.000Z")
        self.assertEqual(before, "2026-10-25T23:00:00.000Z")

    def test_early_morning_still_uses_calendar_day(self) -> None:
        now = datetime(2026, 10, 26, 3, 0, tzinfo=SHANGHAI)
        after, before = cision_lib.shanghai_window(now)
        self.assertEqual(after, "2026-10-24T23:00:00.000Z")
        self.assertEqual(before, "2026-10-25T23:00:00.000Z")

    def test_query_percent_encodes_brackets(self) -> None:
        query = cision_lib.mentions_query("2026-10-24T23:00:00.000Z", "2026-10-25T23:00:00.000Z", 1, 4999)
        self.assertIn("filter%5Brange%5D%5Bafter%5D=2026-10-24T23%3A00%3A00.000Z", query)
        self.assertIn("filter%5Brange%5D%5Bbefore%5D=2026-10-25T23%3A00%3A00.000Z", query)
        self.assertIn("pagination%5Bpage%5D=1", query)
        self.assertIn("pagination%5Bpage_size%5D=4999", query)
        self.assertNotIn("filter[range]", query)
        self.assertNotIn("[", query)

    def test_page_size_5000_rejected(self) -> None:
        with self.assertRaises(RuntimeError):
            cision_lib.validate_page_size(5000)

    def test_large_page_does_not_request_illegal_next_page(self) -> None:
        calls: list[int] = []

        def fetch(page_no: int, page_size: int, after: str, before: str) -> str:
            calls.append(page_no)
            self.assertEqual(page_size, 4999)
            if page_no == 1:
                return page("id,title", "1,a", "2,b")
            raise AssertionError("不应请求会使 page*page_size>=5000 的下一页")

        header, rows, pages = cision_lib.collect_pages(fetch, 4999, "a", "b")
        self.assertEqual(header, ["id", "title"])
        self.assertEqual(rows, [["1", "a"], ["2", "b"]])
        self.assertEqual(pages, 1)
        self.assertEqual(calls, [1])

    def test_pagination_stops_on_page_without_data_rows(self) -> None:
        calls: list[int] = []

        def fetch(page_no: int, page_size: int, after: str, before: str) -> str:
            calls.append(page_no)
            self.assertEqual(page_size, 2)
            if page_no == 1:
                return page("id,title", "1,a", "2,b")
            if page_no == 2:
                return page("id,title", "3,c")
            return page("id,title")

        header, rows, pages = cision_lib.collect_pages(fetch, 2, "a", "b")
        self.assertEqual(header, ["id", "title"])
        self.assertEqual(rows, [["1", "a"], ["2", "b"], ["3", "c"]])
        self.assertEqual(pages, 2)
        self.assertEqual(calls, [1, 2, 3])

    def test_dedup_file_rule(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cision-mentions-") as temporary:
            root = Path(temporary) / "out"
            seen: list[int] = []

            def fetch(page_no: int, page_size: int, after: str, before: str) -> str:
                seen.append(page_no)
                if page_no == 1:
                    return page("id,title", "10,one", "11,two")
                return "id,title\n"

            now = datetime(2026, 10, 26, 18, 0, tzinfo=SHANGHAI)
            first = cision_lib.export_mentions(
                stream_id="1017610",
                output_dir=root,
                fetch_page=fetch,
                now=now,
                page_size=10,
            )
            self.assertFalse(first["previous_exists"])
            self.assertEqual(first["full_rows"], 2)
            self.assertEqual(first["delta_rows"], 2)
            latest = Path(first["latest_csv"])
            self.assertTrue(latest.is_file())
            self.assertEqual(cision_lib.load_previous_ids(latest), {"10", "11"})

            def fetch_again(page_no: int, page_size: int, after: str, before: str) -> str:
                if page_no == 1:
                    return page("id,title", "11,two", "12,three")
                return "id,title\n"

            second = cision_lib.export_mentions(
                stream_id="1017610",
                output_dir=root,
                fetch_page=fetch_again,
                now=now,
                page_size=10,
            )
            self.assertTrue(second["previous_exists"])
            self.assertEqual(second["previous_ids"], 2)
            self.assertEqual(second["full_rows"], 2)
            self.assertEqual(second["delta_rows"], 1)
            delta_text = Path(second["delta_csv"]).read_text(encoding="utf-8")
            self.assertEqual(delta_text, "id,title\n12,three\n")
            self.assertEqual(cision_lib.load_previous_ids(latest), {"11", "12"})
            self.assertTrue(seen)

    def test_push_failure_does_not_replace_latest(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cision-mentions-") as temporary:
            root = Path(temporary) / "out"
            now = datetime(2026, 10, 26, 18, 0, tzinfo=SHANGHAI)

            def fetch(page_no: int, page_size: int, after: str, before: str) -> str:
                if page_no == 1:
                    return page("id,title", "10,one")
                return "id,title\n"

            cision_lib.export_mentions(
                stream_id="7",
                output_dir=root,
                fetch_page=fetch,
                now=now,
                page_size=10,
            )

            def fetch_new(page_no: int, page_size: int, after: str, before: str) -> str:
                if page_no == 1:
                    return page("id,title", "10,one", "99,new")
                return "id,title\n"

            def fail_push(delta_path: Path, summary: dict) -> None:
                raise RuntimeError("push failed")

            with self.assertRaises(RuntimeError):
                cision_lib.export_mentions(
                    stream_id="7",
                    output_dir=root,
                    fetch_page=fetch_new,
                    now=now,
                    page_size=10,
                    push=fail_push,
                )
            latest = root / "state" / "7" / "latest.csv"
            self.assertEqual(cision_lib.load_previous_ids(latest), {"10"})

    def test_output_dir_inside_repo_is_rejected(self) -> None:
        inside = Path("/workspace/cision-mentions-output")
        with self.assertRaises(RuntimeError):
            cision_lib.ensure_output_dir(inside)
        self.assertFalse(inside.exists())

    def test_feishu_chat_is_fixed(self) -> None:
        import inspect

        import feishu_push

        self.assertEqual(feishu_push.FEISHU_CHAT_ID, "oc_27040b0dc3a733ab164199154c489fad")
        self.assertEqual(feishu_push.FEISHU_RECEIVE_ID_TYPE, "chat_id")
        self.assertEqual(list(inspect.signature(feishu_push.push_delta).parameters), ["delta_path", "summary"])
        scripts = Path(__file__).resolve().parent
        export_source = (scripts / "export_mentions.py").read_text(encoding="utf-8")
        push_source = (scripts / "feishu_push.py").read_text(encoding="utf-8")
        self.assertNotIn("feishu-receive", export_source)
        self.assertNotIn("FEISHU_CHAT_ID", export_source)
        self.assertNotIn("os.environ.get(\"FEISHU_CHAT", push_source)
        self.assertEqual(push_source.count("oc_27040b0dc3a733ab164199154c489fad"), 1)
        self.assertEqual(feishu_push.BITABLE_SYNC_STREAM_ID, "1017610")
        self.assertEqual(feishu_push.WIKI_NODE_TOKEN, "ODp7wESdDiXrHjk7tEPcsQrSn6d")
        self.assertEqual(feishu_push.BITABLE_APP_TOKEN, "ByFgbm0xRaCBD2s8ohtcg0kgnWc")
        self.assertEqual(feishu_push.BITABLE_TABLE_ID, "tblpvXJxxasNjP5e")
        self.assertEqual(feishu_push.BITABLE_TABLE_NAME, "百度海外竞品最新数据")
        self.assertNotIn("ByFgbm0xRaCBD2s8ohtcg0kgnWc", export_source)
        self.assertNotIn("tblpvXJxxasNjP5e", export_source)
        self.assertNotIn("--wiki", export_source)
        self.assertNotIn("--table", export_source)
        skill = (scripts.parent / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("`0 23 * * *`", skill)
        self.assertIn("`30 10 * * *`", skill)
        self.assertNotIn("07:05", skill)
        self.assertNotIn("5 23", skill)
        self.assertIn('"PATCH"', push_source)
        self.assertNotIn('"PUT"', push_source)
        self.assertIn("PATCH", skill)
        self.assertNotIn("`PUT .../tables/{table}`", skill)

    def test_table_rename_uses_patch(self) -> None:
        import feishu_push

        calls: list[tuple[str, dict | None]] = []
        original = feishu_push._request

        def fake_request(url: str, method: str, payload: dict | None = None, token: str | None = None) -> dict:
            calls.append((method, payload))
            self.assertIn("/tables/" + feishu_push.BITABLE_TABLE_ID, url)
            return {"code": 0, "data": {}}

        feishu_push._request = fake_request
        try:
            client = feishu_push.FeishuBitable()
            client._bearer = lambda: "token"  # type: ignore[method-assign]
            client._get_data = lambda url: {  # type: ignore[method-assign]
                "items": [{"table_id": feishu_push.BITABLE_TABLE_ID, "name": "数据表"}],
                "has_more": False,
            }
            client.ensure_name()
        finally:
            feishu_push._request = original
        self.assertEqual(calls, [("PATCH", {"name": feishu_push.BITABLE_TABLE_NAME})])

    def test_bitable_sync_order_and_full_write(self) -> None:
        import feishu_push

        calls: list[object] = []

        class Fake:
            def list_fields(self) -> list[str]:
                calls.append("fields")
                return ["文本", "id", "title"]

            def list_records(self) -> list[dict]:
                calls.append("records")
                return [
                    {"record_id": "rec_old", "fields": {"id": [{"text": "10", "type": "text"}], "文本": "placeholder"}},
                    {"record_id": "rec_blank", "fields": {"文本": "empty"}},
                ]

            def create_field(self, name: str) -> None:
                calls.append(("field", name))

            def ensure_name(self) -> None:
                calls.append("name")

            def delete_records(self, record_ids: list[str]) -> None:
                calls.append(("delete", list(record_ids)))

            def create_records(self, field_rows: list[dict]) -> None:
                calls.append(("write", field_rows))

        pushed: list[int] = []

        def push(delta_path: Path, summary: dict) -> None:
            pushed.append(summary["delta_rows"])
            calls.append("push")
            self.assertEqual(delta_path.read_text(encoding="utf-8"), "id,title\n12,new\n")

        with tempfile.TemporaryDirectory(prefix="cision-mentions-") as temporary:
            delta_path = Path(temporary) / "delta.csv"
            summary = feishu_push.sync_1017610_baseline(
                ["id", "title"],
                [["10", "old"], ["12", "new"]],
                delta_path,
                {"delta_rows": 0},
                client=Fake(),
                push=push,
            )
        self.assertEqual(
            calls,
            ["fields", "records", "name", ("delete", ["rec_old", "rec_blank"]), ("write", [{"id": "10", "title": "old"}, {"id": "12", "title": "new"}]), "push"],
        )
        self.assertEqual(pushed, [1])
        self.assertEqual(summary["bitable_written"], 2)
        self.assertEqual(summary["bitable_deleted"], 2)
        self.assertEqual(summary["previous_ids"], 1)
        self.assertEqual(summary["feishu"], "sent")

    def test_bitable_read_failure_does_not_delete(self) -> None:
        import feishu_push

        class Fake:
            def list_fields(self) -> list[str]:
                raise RuntimeError("HTTP 403")

            def list_records(self) -> list[dict]:
                raise AssertionError("不应继续读记录")

            def delete_records(self, record_ids: list[str]) -> None:
                raise AssertionError("不应删除")

            def create_records(self, field_rows: list[dict]) -> None:
                raise AssertionError("不应写入")

            def create_field(self, name: str) -> None:
                raise AssertionError("不应建字段")

            def ensure_name(self) -> None:
                raise AssertionError("不应改表名")

        def push(delta_path: Path, summary: dict) -> None:
            raise AssertionError("不应推送")

        with self.assertRaises(RuntimeError):
            feishu_push.sync_1017610_baseline(["id"], [["1"]], Path("/tmp/ignored-delta.csv"), {}, client=Fake(), push=push)

    def test_missing_id_field_means_full_delta(self) -> None:
        import feishu_push

        written: list[dict] = []

        class Fake:
            def list_fields(self) -> list[str]:
                return ["文本"]

            def list_records(self) -> list[dict]:
                return [{"record_id": "rec_placeholder", "fields": {"文本": "占位"}}]

            def create_field(self, name: str) -> None:
                return None

            def ensure_name(self) -> None:
                return None

            def delete_records(self, record_ids: list[str]) -> None:
                self.deleted = record_ids

            def create_records(self, field_rows: list[dict]) -> None:
                written.extend(field_rows)

        fake = Fake()

        def push(delta_path: Path, summary: dict) -> None:
            self.assertEqual(summary["delta_rows"], 1)

        with tempfile.TemporaryDirectory(prefix="cision-mentions-") as temporary:
            summary = feishu_push.sync_1017610_baseline(
                ["id"],
                [["99"]],
                Path(temporary) / "delta.csv",
                {},
                client=fake,
                push=push,
            )
        self.assertEqual(fake.deleted, ["rec_placeholder"])
        self.assertEqual(written, [{"id": "99"}])
        self.assertEqual(summary["previous_ids"], 0)
        self.assertFalse(summary["previous_exists"])

    def test_1017610_does_not_write_latest_csv(self) -> None:
        import export_mentions

        def fetch(page_no: int, page_size: int, after: str, before: str) -> str:
            if page_no == 1:
                return page("id,title", "10,one")
            return "id,title\n"

        def sync(header: list[str], rows: list[list[str]], delta_path: Path, summary: dict) -> dict:
            cision_lib.write_csv(delta_path, header, rows)
            updated = dict(summary)
            updated["delta_rows"] = len(rows)
            updated["previous_ids"] = 0
            updated["previous_exists"] = False
            updated["feishu"] = "sent"
            updated["bitable_deleted"] = 5
            updated["bitable_written"] = len(rows)
            updated["dedup"] = "bitable"
            return updated

        with tempfile.TemporaryDirectory(prefix="cision-mentions-") as temporary:
            root = Path(temporary) / "out"
            now = datetime(2026, 10, 26, 18, 30, tzinfo=SHANGHAI)
            summary = export_mentions.run_export(
                stream_id="1017610",
                output_dir=root,
                fetch_page=fetch,
                page_size=10,
                push_feishu=False,
                now=now,
                sync=sync,
            )
            self.assertFalse((root / "state" / "1017610" / "latest.csv").exists())
            self.assertEqual(summary["full_rows"], 1)
            self.assertEqual(summary["bitable_written"], 1)
            self.assertTrue((root / "runs" / "1017610").exists())

    def test_other_stream_still_uses_latest_csv(self) -> None:
        import export_mentions

        def fetch(page_no: int, page_size: int, after: str, before: str) -> str:
            if page_no == 1:
                return page("id,title", "10,one")
            return "id,title\n"

        def sync(*args, **kwargs):
            raise AssertionError("其他 stream 不应同步多维表格")

        with tempfile.TemporaryDirectory(prefix="cision-mentions-") as temporary:
            root = Path(temporary) / "out"
            now = datetime(2026, 10, 26, 18, 30, tzinfo=SHANGHAI)
            summary = export_mentions.run_export(
                stream_id="8",
                output_dir=root,
                fetch_page=fetch,
                page_size=10,
                push_feishu=False,
                now=now,
                sync=sync,
            )
            self.assertEqual(cision_lib.load_previous_ids(root / "state" / "8" / "latest.csv"), {"10"})
            self.assertEqual(summary["delta_rows"], 1)
            self.assertEqual(summary["feishu"], "skipped")

    def test_commands_stay_separate(self) -> None:
        scripts = Path(__file__).resolve().parent
        export_source = (scripts / "export_mentions.py").read_text(encoding="utf-8")
        list_source = (scripts / "list_streams.py").read_text(encoding="utf-8")
        self.assertNotIn("/public/api/v2/streams", export_source)
        self.assertNotIn("/public/api/v2/mentions", list_source)
        self.assertNotIn("fetch_streams", export_source)

    def test_summary_text_has_counts_only(self) -> None:
        text = feishu_summary()
        self.assertNotIn("title", text)
        self.assertIn("delta_rows=1", text)

    def test_stream_id_rejects_path_characters(self) -> None:
        with self.assertRaises(RuntimeError):
            cision_lib.normalize_stream_id("../1017610")


def feishu_summary() -> str:
    import feishu_push

    return feishu_push.summary_text(
        {
            "stream_id": "1017610",
            "after": "2026-10-24T23:00:00.000Z",
            "before": "2026-10-25T23:00:00.000Z",
            "full_rows": 2,
            "previous_exists": False,
            "delta_rows": 1,
        }
    )


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CisionMentionsTest)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
