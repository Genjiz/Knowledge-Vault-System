import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "scopus" / "complete_page.json"


class FakeResponse:
    def __init__(self, payload=None, status_code=200):
        self.payload = payload or {}
        self.status_code = status_code
        self.headers = {}
        self.text = json.dumps(self.payload)

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, responses):
        self.trust_env = True
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


class ScopusSourceTestCase(unittest.TestCase):
    def setUp(self):
        self.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_fetch_year_maps_complete_entries(self):
        from app.collection.sources.scopus import ScopusSource

        session = FakeSession([FakeResponse(self.fixture)])
        source = ScopusSource(api_key_loader=lambda: "test-key", session_factory=lambda: session)

        payload = source.fetch_issue("IP&M", 2025, "ignored", issn="0306-4573")

        self.assertFalse(session.trust_env)
        self.assertEqual(payload["issue"]["issue"], "year")
        self.assertIsNone(payload["issue"]["volume"])
        self.assertEqual(payload["issue"]["paper_count_hint"], 2)
        first = payload["papers"][0]
        self.assertEqual(first["source_identifier"], "2-s2.0-TEST001")
        self.assertEqual(first["authors"], "Ada Lovelace, Turing, A.")
        self.assertEqual(first["volume"], "62")
        self.assertEqual(first["issue"], "2PA")
        self.assertEqual(first["doi"], "10.1016/j.ipm.2025.100001")
        self.assertEqual(first["detail_url"], "https://www.sciencedirect.com/science/article/pii/S0306457325000012")
        self.assertEqual(json.loads(first["keywords_json"]), ["retrieval", "knowledge systems"])
        self.assertEqual(json.loads(first["source_ref_json"]), {
            "eid": "2-s2.0-TEST001",
            "pii": "S0306457325000012",
            "doi": "10.1016/j.ipm.2025.100001",
        })
        params = session.calls[0][1]["params"]
        self.assertEqual(params["query"], "ISSN(0306-4573) AND PUBYEAR = 2025")
        self.assertEqual(params["view"], "COMPLETE")
        self.assertEqual(params["count"], 25)
        second = payload["papers"][1]
        self.assertEqual(second["source_identifier"], "SCOPUS_ID:TEST002")
        self.assertEqual(second["pages"], "113-120")
        self.assertEqual(second["detail_url"], "https://doi.org/10.1016/j.ipm.2025.100002")

    def test_fetch_year_paginates_and_deduplicates(self):
        from app.collection.sources.scopus import ScopusSource

        first = {"search-results": {"opensearch:totalResults": "3", "entry": self.fixture["search-results"]["entry"]}}
        duplicate = dict(self.fixture["search-results"]["entry"][0])
        second = {"search-results": {"opensearch:totalResults": "3", "entry": [duplicate]}}
        session = FakeSession([FakeResponse(first), FakeResponse(second)])
        source = ScopusSource(
            api_key_loader=lambda: "test-key",
            session_factory=lambda: session,
            sleep=lambda _: None,
        )

        payload = source.fetch_issue("IP&M", 2025, None, issn="0306-4573")

        self.assertEqual(len(session.calls), 2)
        self.assertEqual(session.calls[1][1]["params"]["start"], 25)
        self.assertEqual(len(payload["papers"]), 2)

    def test_drops_entries_without_title_or_identity(self):
        from app.collection.sources.scopus import ScopusSource

        payload = {"search-results": {"opensearch:totalResults": "2", "entry": [
            {"eid": "2-s2.0-NOTITLE"},
            {"dc:title": "No identity"},
        ]}}
        source = ScopusSource(
            api_key_loader=lambda: "test-key",
            session_factory=lambda: FakeSession([FakeResponse(payload)]),
        )

        result = source.fetch_issue("IP&M", 2025, None, issn="0306-4573")

        self.assertEqual(result["papers"], [])
        self.assertEqual(result["issue"]["dropped_paper_count"], 2)

    def test_accepts_pii_without_doi(self):
        from app.collection.sources.scopus import ScopusSource

        payload = {"search-results": {"opensearch:totalResults": "1", "entry": [
            {"dc:title": "PII only", "pii": "S0306457325000099"}
        ]}}
        source = ScopusSource(
            api_key_loader=lambda: "test-key",
            session_factory=lambda: FakeSession([FakeResponse(payload)]),
        )

        result = source.fetch_issue("IP&M", 2025, None, issn="0306-4573")

        self.assertEqual(len(result["papers"]), 1)
        self.assertIsNone(result["papers"][0]["doi"])
        self.assertIn("S0306457325000099", result["papers"][0]["detail_url"])

    def test_empty_result_returns_empty_year_payload(self):
        from app.collection.sources.scopus import ScopusSource

        source = ScopusSource(
            api_key_loader=lambda: "test-key",
            session_factory=lambda: FakeSession([
                FakeResponse({"search-results": {"opensearch:totalResults": "0", "entry": []}})
            ]),
        )

        result = source.fetch_issue("IP&M", 2025, None, issn="0306-4573")

        self.assertEqual(result["issue"]["paper_count_hint"], 0)
        self.assertEqual(result["papers"], [])

    def test_missing_key_or_issn_fails_before_network(self):
        from app.collection.sources.base import ProviderError
        from app.collection.sources.scopus import ScopusSource

        source = ScopusSource(api_key_loader=lambda: None)
        with self.assertRaisesRegex(ProviderError, "API Key"):
            source.fetch_issue("IP&M", 2025, None, issn="0306-4573")

        source = ScopusSource(api_key_loader=lambda: "test-key")
        with self.assertRaisesRegex(ProviderError, "ISSN"):
            source.fetch_issue("IP&M", 2025, None, issn="")

    def test_auth_errors_include_network_entitlement_hint(self):
        from app.collection.sources.base import ProviderError
        from app.collection.sources.scopus import ScopusSource

        source = ScopusSource(
            api_key_loader=lambda: "test-key",
            session_factory=lambda: FakeSession([FakeResponse(status_code=403)]),
        )
        with self.assertRaisesRegex(ProviderError, "校园网|aTrust"):
            source.fetch_issue("IP&M", 2025, None, issn="0306-4573")

    def test_retries_rate_limit_then_succeeds(self):
        from app.collection.sources.scopus import ScopusSource

        session = FakeSession(
            [FakeResponse(status_code=429), FakeResponse(self.fixture)]
        )
        sleeps = []
        source = ScopusSource(
            api_key_loader=lambda: "test-key",
            session_factory=lambda: session,
            sleep=sleeps.append,
        )

        payload = source.fetch_issue("IP&M", 2025, None, issn="0306-4573")

        self.assertEqual(len(payload["papers"]), 2)
        self.assertEqual(len(session.calls), 2)
        self.assertEqual(sleeps, [1.0])

    def test_retries_server_error_then_succeeds(self):
        from app.collection.sources.scopus import ScopusSource

        session = FakeSession(
            [FakeResponse(status_code=503), FakeResponse(self.fixture)]
        )
        source = ScopusSource(
            api_key_loader=lambda: "test-key",
            session_factory=lambda: session,
            sleep=lambda _: None,
        )

        result = source.fetch_issue("IP&M", 2025, None, issn="0306-4573")

        self.assertEqual(len(result["papers"]), 2)
        self.assertEqual(len(session.calls), 2)

    def test_fails_instead_of_silently_crossing_pagination_limit(self):
        from app.collection.sources.base import ProviderError
        from app.collection.sources.scopus import ScopusSource

        payload = {"search-results": {"opensearch:totalResults": "26", "entry": [
            {"dc:title": "First", "eid": "2-s2.0-FIRST"}
        ]}}
        source = ScopusSource(
            api_key_loader=lambda: "test-key",
            session_factory=lambda: FakeSession([FakeResponse(payload)]),
            sleep=lambda _: None,
        )

        with mock.patch("app.collection.sources.scopus.MAX_START", 25):
            with self.assertRaisesRegex(ProviderError, "分页上限"):
                source.fetch_issue("IP&M", 2025, None, issn="0306-4573")

    def test_connection_uses_standard_single_result(self):
        from app.collection.sources.scopus import ScopusSource

        session = FakeSession([
            FakeResponse({"search-results": {
                "opensearch:totalResults": "10",
                "entry": [{"dc:title": "Connection probe", "eid": "2-s2.0-PROBE"}],
            }})
        ])
        source = ScopusSource(api_key_loader=lambda: "test-key", session_factory=lambda: session)

        result = source.test_connection(journal_name="IP&M", issn="0306-4573")

        self.assertEqual(result["status"], "ok")
        params = session.calls[0][1]["params"]
        self.assertEqual(params["view"], "STANDARD")
        self.assertEqual(params["count"], 1)
        self.assertEqual(len(session.calls), 1)

    def test_default_key_loader_prefers_current_environment(self):
        from app.collection.sources.scopus import load_elsevier_api_key

        with mock.patch.dict(os.environ, {"ELSEVIER_API_KEY": " current-key "}):
            self.assertEqual(load_elsevier_api_key(), "current-key")


if __name__ == "__main__":
    unittest.main()
