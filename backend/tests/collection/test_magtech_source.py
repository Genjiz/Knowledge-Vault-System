"""Magtech（玛格泰克）期刊官网采集源测试。

解析逻辑全部使用 tests/fixtures/magtech/ 下的真实站点响应做离线验证，
网络调用用假 session 覆盖，不发起真实请求。
"""
import sys
import json
import unittest
from pathlib import Path

import requests

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "magtech"

BASE_URL = "https://qbxb.istic.ac.cn"


def load_fixture(name):
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


class FakeResponse:
    def __init__(self, text="", status_code=200, content=None, headers=None):
        self.text = text
        self.content = content if content is not None else text.encode("utf-8")
        self.headers = headers or {}
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class RoutingSession:
    """按 URL 片段路由到固定响应的假 session，并记录调用历史。"""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def get(self, url, timeout=None, **kwargs):
        self.calls.append(url)
        for fragment, payload in self.routes.items():
            if fragment in url:
                if isinstance(payload, Exception):
                    raise payload
                if isinstance(payload, FakeResponse):
                    return payload
                return FakeResponse(payload)
        return FakeResponse("", status_code=404)


class FailingSession:
    """前 fail_times 次调用失败，之后返回指定响应。"""

    def __init__(self, fail_times, response):
        self.fail_times = fail_times
        self.response = response
        self.calls = []

    def get(self, url, timeout=None, **kwargs):
        self.calls.append(url)
        if len(self.calls) <= self.fail_times:
            raise requests.RequestException("connection reset")
        return FakeResponse(self.response)


def build_issue_session():
    """构造覆盖「年页 -> 期页 -> 题录/摘要」全链路的假 session。"""
    return RoutingSession(
        {
            "showTenYearVolumnDetail.do": load_fixture("qbxb_year_2026.html"),
            "volumn_1243.shtml": load_fixture("qbxb_volumn_2026_07.html"),
            "fileType=BibTeX": load_fixture("article_1044.bib"),
            "fileType=EndNote": load_fixture("article_1044.ris"),
        }
    )


class MagtechParsingTestCase(unittest.TestCase):
    def test_parse_year_page_extracts_all_issues(self):
        from app.collection.sources.magtech import parse_year_page

        issues = parse_year_page(load_fixture("qbxb_year_2026.html"), 2026)

        self.assertEqual(len(issues), 7)
        self.assertEqual([item["issue"] for item in issues], ["1", "2", "3", "4", "5", "6", "7"])

    def test_parse_year_page_maps_issue_to_volumn_id(self):
        from app.collection.sources.magtech import parse_year_page

        issues = parse_year_page(load_fixture("qbxb_year_2026.html"), 2026)
        by_issue = {item["issue"]: item for item in issues}

        self.assertEqual(by_issue["7"]["volumn_id"], "1243")
        self.assertEqual(by_issue["7"]["volume"], "45")
        self.assertEqual(by_issue["7"]["pages"], "925-1082")
        self.assertEqual(by_issue["7"]["published_at"], "2026-07-31")
        self.assertEqual(by_issue["7"]["year"], 2026)

    def test_parse_year_page_ignores_cover_image_rows(self):
        """封面图区块同样含 volumn 链接但不带卷期描述，必须被过滤。"""
        from app.collection.sources.magtech import parse_year_page

        issues = parse_year_page(load_fixture("qbxb_year_2026.html"), 2026)

        for item in issues:
            self.assertTrue(item["issue"])
            self.assertTrue(item["volumn_id"])
            self.assertTrue(item["volume"])

    def test_parse_year_page_returns_empty_for_unrelated_page(self):
        from app.collection.sources.magtech import parse_year_page

        self.assertEqual(parse_year_page("<html><body>no data</body></html>", 2026), [])

    def test_parse_volumn_page_extracts_ordered_article_ids(self):
        from app.collection.sources.magtech import parse_volumn_page

        article_ids = parse_volumn_page(load_fixture("qbxb_volumn_2026_07.html"))

        self.assertEqual(article_ids, ["1044", "1045", "1046", "1047", "1048", "1049", "1050", "1051", "1052", "1053"])

    def test_parse_bibtex_extracts_metadata(self):
        from app.collection.sources.magtech import parse_bibtex

        data = parse_bibtex(load_fixture("article_1044.bib"))

        self.assertEqual(data["title"], "基于多粒度语义计算的技术谱系构建及创新路径识别研究")
        self.assertEqual(data["authors"], "杨金庆, 罗星雨, 熊炳桥, 曹高辉")
        self.assertEqual(data["journal"], "情报学报")
        self.assertEqual(data["year"], "2026")
        self.assertEqual(data["volume"], "45")
        self.assertEqual(data["number"], "7")
        self.assertEqual(data["doi"], "10.3772/j.issn.1000-0135.2026.07.001")
        self.assertEqual(data["keywords"], ["技术谱系", "语义关联", "专利相似度", "创新路径"])
        self.assertEqual(data["url"], "https://qbxb.istic.ac.cn/CN/abstract/article_1044.shtml")

    def test_parse_bibtex_tolerates_empty_payload(self):
        from app.collection.sources.magtech import parse_bibtex

        data = parse_bibtex("")

        self.assertEqual(data["title"], "")
        self.assertEqual(data["keywords"], [])

    def test_parse_bibtex_strips_only_balanced_title_markup(self):
        from app.collection.sources.magtech import parse_bibtex

        balanced = parse_bibtex("@article{x, title={<bold>XGBoost</bold>方法}}")
        unbalanced = parse_bibtex("@article{x, title={<bold>XGBoost方法}}")

        self.assertEqual(balanced["title"], "XGBoost方法")
        self.assertEqual(unbalanced["title"], "<bold>XGBoost方法")

    def test_parse_endnote_extracts_abstract_and_publish_date(self):
        from app.collection.sources.magtech import parse_endnote

        data = parse_endnote(load_fixture("article_1044.ris"))

        self.assertIn("随着全球科技竞争加剧", data["abstract"])
        self.assertEqual(data["published_at"], "2026-07-24")
        self.assertEqual(data["pages"], "925-939")

    def test_parse_endnote_tolerates_empty_payload(self):
        from app.collection.sources.magtech import parse_endnote

        data = parse_endnote("")

        self.assertEqual(data["abstract"], "")
        self.assertEqual(data["published_at"], "")


class MagtechSourceContractTestCase(unittest.TestCase):
    def _make_source(self, session, **kwargs):
        from app.collection.sources.magtech import MagtechSource

        return MagtechSource(base_url=BASE_URL, session=session, request_interval=0, **kwargs)

    def test_source_declares_capabilities(self):
        from app.collection.sources.magtech import MagtechSource

        self.assertEqual(MagtechSource.source_id, "magtech")
        self.assertEqual(MagtechSource.region, "domestic")
        self.assertTrue(MagtechSource.capabilities["list_issues"])
        self.assertFalse(MagtechSource.capabilities["needs_browser"])
        self.assertEqual([f["key"] for f in MagtechSource.config_fields], ["base_url"])

    def test_requires_base_url(self):
        from app.collection.sources.magtech import MagtechSource

        with self.assertRaises(ValueError):
            MagtechSource()

    def test_list_issues_returns_sorted_issues(self):
        session = build_issue_session()
        source = self._make_source(session)

        issues = source.list_issues("情报学报", 2026)

        self.assertEqual([item["issue"] for item in issues], ["1", "2", "3", "4", "5", "6", "7"])
        self.assertEqual(issues[-1]["source_url"], f"{BASE_URL}/CN/volumn/volumn_1243.shtml")

    def test_fetch_issue_returns_payload_compatible_with_existing_sources(self):
        session = build_issue_session()
        source = self._make_source(session)

        payload = source.fetch_issue("情报学报", 2026, "7")

        issue = payload["issue"]
        self.assertEqual(issue["source_type"], "magtech")
        self.assertEqual(issue["region"], "domestic")
        self.assertEqual(issue["journal_name"], "情报学报")
        self.assertEqual(issue["journal_slug"], "情报学报")
        self.assertEqual(issue["year"], 2026)
        self.assertEqual(issue["issue"], "7")
        self.assertEqual(issue["volume"], "45")
        self.assertEqual(issue["language"], "zh")
        self.assertEqual(issue["source_url"], f"{BASE_URL}/CN/volumn/volumn_1243.shtml")

        self.assertEqual(len(payload["papers"]), 10)
        first = payload["papers"][0]
        self.assertEqual(first["title"], "基于多粒度语义计算的技术谱系构建及创新路径识别研究")
        self.assertEqual(first["title_zh"], first["title"])
        self.assertEqual(first["authors"], "杨金庆, 罗星雨, 熊炳桥, 曹高辉")
        self.assertIn("随着全球科技竞争加剧", first["abstract"])
        self.assertEqual(first["pages"], "925-939")
        self.assertEqual(first["doi"], "10.3772/j.issn.1000-0135.2026.07.001")
        self.assertEqual(first["source_identifier"], "10.3772/j.issn.1000-0135.2026.07.001")
        self.assertEqual(json.loads(first["source_ref_json"]), {"article_id": "1044"})
        self.assertEqual(first["detail_url"], "https://qbxb.istic.ac.cn/CN/abstract/article_1044.shtml")
        self.assertEqual(first["published_at"], "2026-07-24")
        self.assertEqual(first["sort_index"], 0)
        self.assertEqual(first["translation_status"], "completed")
        self.assertEqual(first["keywords_json"], '["技术谱系", "语义关联", "专利相似度", "创新路径"]')

    def test_fetch_issue_unknown_issue_raises_clear_error(self):
        from app.collection.sources.base import ProviderError

        source = self._make_source(build_issue_session())

        with self.assertRaises(ProviderError) as ctx:
            source.fetch_issue("情报学报", 2026, "99")

        self.assertIn("2026", str(ctx.exception))
        self.assertIn("99", str(ctx.exception))

    def test_retries_transient_errors(self):
        source = self._make_source(
            FailingSession(fail_times=2, response=load_fixture("qbxb_year_2026.html")),
            max_attempts=3,
        )

        issues = source.list_issues("情报学报", 2026)

        self.assertEqual(len(issues), 7)
        self.assertEqual(len(source._session.calls), 3)

    def test_gives_up_after_max_attempts(self):
        from app.collection.sources.base import ProviderError

        session = FailingSession(fail_times=99, response="")
        source = self._make_source(session, max_attempts=2)

        with self.assertRaises(ProviderError):
            source.list_issues("情报学报", 2026)

        self.assertEqual(len(session.calls), 2)

    def test_client_error_is_not_retried(self):
        """4xx 属确定性失败，重试无意义，应只请求一次。"""
        from app.collection.sources.base import ProviderError

        session = RoutingSession({"showTenYearVolumnDetail.do": FakeResponse("", status_code=404)})
        source = self._make_source(session, max_attempts=3)

        with self.assertRaises(ProviderError):
            source.list_issues("情报学报", 2026)

        self.assertEqual(len(session.calls), 1)

    def test_article_metadata_failure_does_not_abort_whole_issue(self):
        """单篇题录拉取失败时应跳过该篇，而不是让整期采集失败。"""
        session = RoutingSession(
            {
                "showTenYearVolumnDetail.do": load_fixture("qbxb_year_2026.html"),
                "volumn_1243.shtml": load_fixture("qbxb_volumn_2026_07.html"),
            }
        )
        source = self._make_source(session)

        payload = source.fetch_issue("情报学报", 2026, "7")

        self.assertEqual(payload["issue"]["paper_count_hint"], 10)
        self.assertEqual(payload["papers"], [])

    def test_download_pdf_returns_binary_result_and_source_url(self):
        from app.collection.sources.base import PdfDownload

        session = RoutingSession(
            {
                "downloadArticleFile.do": FakeResponse(
                    content=b"%PDF-1.4\nfixture",
                    headers={"Content-Type": "application/x-download"},
                )
            }
        )
        source = self._make_source(session)

        result = source.download_pdf({"article_id": "1044"})

        self.assertIsInstance(result, PdfDownload)
        self.assertEqual(result.content, b"%PDF-1.4\nfixture")
        self.assertEqual(result.content_type, "application/x-download")
        self.assertEqual(
            result.source_url,
            f"{BASE_URL}/CN/article/downloadArticleFile.do?attachType=PDF&id=1044",
        )


if __name__ == "__main__":
    unittest.main()
