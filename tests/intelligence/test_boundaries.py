"""No policy, signer, wallet or upload capability is reachable from the evidence path."""

import ast
import sys
import unittest
from pathlib import Path

from larp.intelligence.common import IntelligenceError
from larp.intelligence.fakes import FakeClock, FakeFilingSource, MemoryArtifacts, MemoryEvidenceStore, require_real
from larp.intelligence.tools import TOOLS, ToolError, run_tool

PACKAGE = Path(__file__).resolve().parents[2] / "larp" / "intelligence"
NETWORK = {"urllib", "socket", "http", "ssl", "requests", "httpx", "aiohttp"}
NETWORK_MODULES = {"edgar.py", "models.py", "providers.py"}  # providers.py: hosted assessor adapters (IDEA-041)


def imports(path: Path) -> set:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


class BoundaryTests(unittest.TestCase):
    def test_imports_are_stdlib_contracts_or_this_package(self):
        for path in sorted(PACKAGE.glob("*.py")):
            for name in imports(path):
                top = name.split(".")[0]
                with self.subTest(module=path.name, imports=name):
                    allowed = (name == "larp.contracts" or name.startswith("larp.intelligence")
                               or top in sys.stdlib_module_names)
                    self.assertTrue(allowed)
                    if top in NETWORK:
                        self.assertIn(path.name, NETWORK_MODULES)

    def test_no_reference_to_signing_policy_execution_or_upload_code(self):
        modules = ("larp.execution", "larp.strategy", "larp.risk", "larp.runtime", "larp.audit", "eth_account",
                   "ai_seeds_sdk", "sign_transaction")
        credentials = ("private_key", "WALLET_MNEMONIC", "AI_SEEDS_SECRET", "BINANCE_SECRET_KEY")
        for path in sorted(PACKAGE.glob("*.py")):
            source = path.read_text(encoding="utf-8")
            # common.py names credential fields only to forbid them in outputs.
            for word in modules + (() if path.name == "common.py" else credentials):
                with self.subTest(module=path.name, word=word):
                    self.assertNotIn(word, source)

    def test_tool_registry_is_exactly_three_read_only_tools(self):
        self.assertEqual(sorted(TOOLS), ["compare_facts", "fetch_document", "prior_context"])

        class State:
            allowed_tools = ("fetch_document", "prior_context", "compare_facts", "sign", "http_get")

        for name in ("sign", "broadcast", "http_get", "web_search", "approve", "log"):
            with self.subTest(tool=name), self.assertRaisesRegex(ToolError, "TOOL_NOT_ALLOWED"):
                run_tool(State(), name, {})

    def test_synthetic_doubles_are_refused_for_live_wiring(self):
        clock = FakeClock(0)
        for double in (clock, FakeFilingSource(clock, {}), MemoryArtifacts(), MemoryEvidenceStore()):
            with self.subTest(double=type(double).__name__), self.assertRaises(IntelligenceError):
                require_real(double)


if __name__ == "__main__":
    unittest.main()
