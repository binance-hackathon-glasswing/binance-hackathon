"""EDGAR parsing, the opt-in HTTP adapter (fake transport only), issuer mapping and configuration."""

import json
import unittest

from larp.intelligence.common import IntelligenceError
from larp.intelligence.config import live_model_settings, load_config, load_registry, sec_user_agent
from larp.intelligence.edgar import (
    EdgarHttpSource, check_identity, history_files, listing_rows, parse_acceptance_ms, parse_filing_index,
    select_documents,
)
from larp.intelligence.issuers import IssuerRegistry

UA = "Glasswing research team-contact@university.edu.sg"


class EdgarParsingTests(unittest.TestCase):
    def test_acceptance_time_needs_an_explicit_offset(self):
        self.assertEqual(parse_acceptance_ms("2026-10-01T20:05:00.000Z"), 1790885100000)
        self.assertEqual(parse_acceptance_ms("2026-10-01T16:05:00-04:00"), 1790885100000)
        for bad in ("2026-10-01T20:05:00", "", None, 5):
            with self.subTest(bad=bad), self.assertRaises((IntelligenceError, ValueError)):
                parse_acceptance_ms(bad)

    def test_listing_rows_flag_malformed_rows(self):
        submissions = {"filings": {"recent": {
            "accessionNumber": ["0000000001-26-000001", "bad", "0000000001-26-000003"],
            "form": ["8-K", "8-K", "10-Q"], "items": ["2.02,9.01", "", ""],
            "acceptanceDateTime": ["2026-10-01T20:05:00.000Z", "2026-10-01T20:05:00.000Z", "not a time"],
            "filingDate": ["2026-10-01"] * 3, "reportDate": ["", "", ""], "primaryDocument": ["a.htm", "b.htm", "c.htm"]}}}
        rows = listing_rows(submissions)
        self.assertEqual([r["malformed"] for r in rows], [None, "ACCESSION", "ACCEPTANCE_TIME"])
        self.assertEqual(rows[0]["items"], ["2.02", "9.01"])

    def test_history_rows_are_merged_and_an_accession_is_kept_once(self):
        recent = {"accessionNumber": ["0000000001-26-000001"], "form": ["8-K"], "items": [""],
                  "acceptanceDateTime": ["2026-10-01T20:05:00.000Z"], "filingDate": ["2026-10-01"],
                  "reportDate": [""], "primaryDocument": ["a.htm"]}
        older = {"accessionNumber": ["0000000001-24-000009", "0000000001-26-000001", ["x"]], "form": ["10-Q"] * 3,
                 "items": [""] * 3, "acceptanceDateTime": ["2024-05-01T20:05:00.000Z"] * 3,
                 "filingDate": ["2024-05-01"] * 3, "reportDate": [""] * 3, "primaryDocument": ["b.htm"] * 3}
        rows = listing_rows({"filings": {"recent": recent}}, (older,))
        self.assertEqual([(r["accession"], r["malformed"]) for r in rows],
                         [("0000000001-26-000001", None), ("0000000001-24-000009", None), (["x"], "ACCESSION")])

    def test_history_files_cover_the_requested_window(self):
        submissions = {"filings": {"recent": {}, "files": [
            {"name": "CIK0009900001-submissions-001.json", "filingFrom": "2024-01-01", "filingTo": "2024-12-31"},
            {"name": "CIK0009900001-submissions-002.json", "filingFrom": "2022-01-01", "filingTo": "2023-12-31"},
            {"name": "CIK0009900001-submissions-003.json"},
            {"name": "../../outside.json", "filingFrom": "2024-01-01", "filingTo": "2024-12-31"}]}}
        window = (parse_acceptance_ms("2024-06-01T00:00:00+00:00"), parse_acceptance_ms("2024-07-01T00:00:00+00:00"))
        names, malformed = history_files(submissions, window)
        self.assertEqual(names, ("CIK0009900001-submissions-001.json", "CIK0009900001-submissions-003.json"))
        self.assertEqual(malformed, ("../../outside.json",))  # never turned into a URL
        late_filed = (parse_acceptance_ms("2025-01-01T02:00:00+00:00"),) * 2  # 2024-12-31 Eastern
        self.assertIn("CIK0009900001-submissions-001.json", history_files(submissions, late_filed)[0])

    def test_identity_check_rejects_wrong_cik_or_name(self):
        check_identity({"cik": "0001045810", "name": "NVIDIA CORP"}, 1045810, "NVIDIA")
        for submissions in ({"cik": "1045811", "name": "NVIDIA CORP"}, {"cik": "1045810", "name": "Other"}):
            with self.subTest(submissions=submissions), self.assertRaises(IntelligenceError):
                check_identity(submissions, 1045810, "NVIDIA")

    def test_index_parsing_and_document_selection_keep_primary(self):
        index = (b"<table><tr><th>Seq</th></tr>"
                 b"<tr><td>1</td><td>Current report</td><td><a href=\"/Archives/x/a8k.htm\">a8k.htm</a></td><td>8-K</td><td>1</td></tr>"
                 b"<tr><td>2</td><td>Press release</td><td><a href=\"ex991.htm\">ex991.htm</a></td><td>EX-99.1</td><td>1</td></tr>"
                 b"<tr><td>3</td><td>Slides</td><td><a href=\"ex992.pdf\">ex992.pdf</a></td><td>EX-99.2</td><td>1</td></tr>"
                 b"<tr><td>4</td><td>Letter</td><td><a href=\"ex993.htm\">ex993.htm</a></td><td>EX-99.3</td><td>1</td></tr></table>")
        rows = parse_filing_index(index)
        self.assertEqual(rows[0], ("8-K", "a8k.htm", "Current report"))
        chosen = select_documents(rows, "a8k.htm", "8-K", 6)
        self.assertEqual([(d["name"], d["role"]) for d in chosen],
                         [("a8k.htm", "PRIMARY"), ("ex991.htm", "EXHIBIT"), ("ex993.htm", "EXHIBIT")])
        self.assertEqual(len(select_documents(rows, "a8k.htm", "8-K", 2)), 2)
        self.assertEqual(select_documents((), "a8k.htm", "8-K", 6)[0]["doc_type"], "8-K")


class EdgarHttpSourceTests(unittest.TestCase):
    def test_refuses_without_declared_user_agent_or_too_fast(self):
        for agent in ("", "anonymous"):
            with self.subTest(agent=agent), self.assertRaises(IntelligenceError):
                EdgarHttpSource(agent)
        with self.assertRaises(IntelligenceError):
            EdgarHttpSource(UA, spacing_s=0.05)

    def test_sends_user_agent_spaces_requests_and_reports_outage(self):
        calls, sleeps = [], []
        body = json.dumps({"cik": "1045810", "name": "NVIDIA CORP", "filings": {"recent": {}}}).encode()

        def http_get(url, headers, timeout):
            calls.append((url, headers["User-Agent"]))
            return (200, "application/json", body) if len(calls) == 1 else (503, None, b"")

        source = EdgarHttpSource(UA, http_get=http_get, clock_ms=lambda: 5, sleep=sleeps.append)
        ok = source.list_filings(1045810)
        self.assertEqual((ok.status, ok.retrieved_ms), ("OK", 5))
        down = source.list_filings(1045810)
        self.assertEqual((down.status, down.error), ("UNAVAILABLE", "HTTP 503"))
        self.assertEqual(calls[0], ("https://data.sec.gov/submissions/CIK0001045810.json", UA))
        self.assertTrue(sleeps and all(s > 0 for s in sleeps))

    def test_network_errors_and_destinations_outside_the_allowlist(self):
        def broken(url, headers, timeout):
            raise TimeoutError("synthetic")

        source = EdgarHttpSource(UA, http_get=broken, sleep=lambda s: None)
        self.assertEqual(source.list_filings(1).status, "UNAVAILABLE")
        with self.assertRaises(IntelligenceError):
            source._fetch("https://attacker.invalid/x")
        with self.assertRaises(IntelligenceError):
            source._fetch("http://www.sec.gov/insecure")


class IssuerMappingTests(unittest.TestCase):
    def setUp(self):
        self.registry = load_registry()

    def test_five_eligible_tokens_map_to_registered_filers(self):
        self.assertEqual(sorted(e.token for e in self.registry.entries), ["GOOGLB", "MSFTB", "NVDAB", "SKHYB", "TSLAB"])
        self.assertEqual(self.registry.by_token("SKHYB").cik, 2120882)
        with self.assertRaises(IntelligenceError):
            self.registry.by_token("NVDA")  # the share ticker is not a token

    def test_form_mapping_follows_filer_class(self):
        nvda, skhy = self.registry.by_token("NVDAB"), self.registry.by_token("SKHYB")
        self.assertEqual([nvda.form_class(f) for f in ("8-K", "10-Q", "10-K", "8-K/A", "6-K", "20-F", "4")],
                         ["CURRENT", "QUARTERLY", "ANNUAL", "CURRENT", None, None, None])
        self.assertEqual([skhy.form_class(f) for f in ("6-K", "20-F", "6-K/A", "8-K", "10-Q", "10-K")],
                         ["CURRENT", "ANNUAL", "CURRENT", None, None, None])

    def test_korean_shares_us_listing_and_token_are_not_interchangeable(self):
        skhy = self.registry.by_token("SKHYB")
        self.assertEqual(self.registry.instrument_relation("XKRX:000660", "XNAS:SKHY"), "SAME_ISSUER_DIFFERENT_INSTRUMENT")
        self.assertEqual(self.registry.instrument_relation("SKHYB", "XKRX:000660"), "SAME_ISSUER_DIFFERENT_INSTRUMENT")
        self.assertEqual(self.registry.instrument_relation("XNAS:GOOGL", "XNAS:GOOG"), "SAME_ISSUER_DIFFERENT_INSTRUMENT")
        self.assertEqual(self.registry.instrument_relation("SKHYB", "NVDAB"), "UNRELATED")
        self.assertIsNone(skhy.security("XNAS:SKHY").ratio_to_common)
        self.assertTrue(all(e.token_underlying is None and e.token_underlying_status == "UNVERIFIED"
                            for e in self.registry.entries))

    def test_registry_rejects_unverified_ratios_and_bad_token_links(self):
        base = {"schema": "IssuerRegistry.v1", "issuers": [{
            "issuer_id": "X", "token": "XB", "cik": 1, "entity_name": "X", "filer_class": "DOMESTIC",
            "reporting_currency": "USD",
            "securities": [{"security_id": "S", "kind": "COMMON", "currency": "USD", "ratio_to_common": [1, 1],
                            "ratio_status": "UNVERIFIED"}],
            "token_underlying": {"security_id": None, "status": "UNVERIFIED"}}]}
        with self.assertRaises(IntelligenceError):
            IssuerRegistry.from_dict(base)
        base["issuers"][0]["securities"][0]["ratio_status"] = "VERIFIED"
        base["issuers"][0]["token_underlying"] = {"security_id": "OTHER", "status": "VERIFIED"}
        with self.assertRaises(IntelligenceError):
            IssuerRegistry.from_dict(base)


class ConfigurationTests(unittest.TestCase):
    def test_development_config_pins_prompt_and_declared_budget(self):
        config = load_config("development")
        self.assertEqual((config.max_tool_calls, config.max_deadline_ms), (6, 180000))
        self.assertEqual(config.tools, ("fetch_document", "prior_context", "compare_facts"))
        self.assertEqual(len(config.prompt_sha256), 64)

    def test_live_startup_fails_while_parameters_are_unset(self):
        with self.assertRaisesRegex(IntelligenceError, "unset"):
            load_config("live")

    def test_live_model_settings_need_explicit_provider_and_one_credential_kind(self):
        with self.assertRaises(IntelligenceError):
            live_model_settings({})
        with self.assertRaises(IntelligenceError):
            live_model_settings({"LARP_MODEL_PROVIDER": "p", "LARP_MODEL_ID": "m",
                                 "LARP_MODEL_API_KEY": "k", "LARP_MODEL_PATH": "/w"})
        settings = live_model_settings({"LARP_MODEL_PROVIDER": "p", "LARP_MODEL_ID": "m", "LARP_MODEL_API_KEY": "s3cret"})
        self.assertNotIn("s3cret", repr(settings))

    def test_sec_user_agent_rejects_placeholders_and_conflicts(self):
        for env in ({}, {"LARP_SEC_USER_AGENT": "Glasswing research <contact email>"},
                    {"LARP_SEC_USER_AGENT": "Glasswing you@example.com"},
                    {"LARP_SEC_USER_AGENT": UA, "SEC_USER_AGENT": "Other a@b.org"}):
            with self.subTest(env=env), self.assertRaises(IntelligenceError):
                sec_user_agent(env)
        self.assertEqual(sec_user_agent({"SEC_USER_AGENT": UA}), UA)

    def test_sec_user_agent_rejects_template_contacts(self):
        # IDEA-066 PC-TERMS01: a copied template passed the old check and sec.gov answered 403.
        refusals = {
            "LARP Team Your Name your.real@email": "template text",
            "LARP Team YourName ops@larp-team.org": "template text",
            "LARP Team firstname.lastname@uni.edu": "template text",
            "LARP Team ops@example.org": "template text",
            "LARP Team ops@larp-team": "no email address",
            "LARP Team ops@larp-team.c": "no email address",
            "LARP Team ops at larp-team.org": "no email address",
            "LARP Team @larp-team.org": "no email address",
            "ops@larp-team.org": "no name",
            "  ops@larp-team.org  ": "no name",
            "   ": "not set",
        }
        for agent, reason in refusals.items():
            with self.subTest(agent=agent), self.assertRaises(IntelligenceError) as caught:
                sec_user_agent({"LARP_SEC_USER_AGENT": agent})
            self.assertIn(reason, str(caught.exception))
            self.assertNotIn("larp-team", str(caught.exception))  # the value is never echoed

    def test_sec_user_agent_accepts_name_and_real_address(self):
        for agent in (UA, "LARP Hackathon Team Jane Tan jane.tan+sec@mail.uni-x.edu.sg",
                      "LARP test runner ops@larp-test.invalid", "LARP Test test-contact@larp.test",
                      "Glasswing ops@larp-team.org (EDGAR research)"):
            with self.subTest(agent=agent):
                self.assertEqual(sec_user_agent({"LARP_SEC_USER_AGENT": f"  {agent} "}), agent)


if __name__ == "__main__":
    unittest.main()
