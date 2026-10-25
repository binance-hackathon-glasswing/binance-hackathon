"""IDEA-096 AL1: executable SELL proof can reach independently guarded cleanup."""
from larp.marketdata.quote_verifier import UntrustedQuoteVerifier
from larp.marketdata.port import TOKENS
from tests.marketdata.test_untrusted_quote_verifier import Harness, profile
from larp.marketdata.web3 import Unavailable


class FlattenAllowance(Harness):
    def test_dirty_skhyb_does_not_deadlock_nvdab_quote_when_recovery_enabled(self):
        record = next(r for r in self.records if r['params']['fromTokenAddress'] == TOKENS['NVDAB'])
        original = self.verifier(record)
        self.rpc.allowances[TOKENS['SKHYB']] = 68939879194155372
        with self.assertRaisesRegex(Unavailable, 'DIRTY_ROUTER_ALLOWANCE:SKHYB'):
            self.observe(record, verifier=original)
        verifier = UntrustedQuoteVerifier(original.decoder, profile(), wallet=original.wallet,
                                          bnb_decimals=18, allowance_recovery=True)
        row = self.observe(record, verifier=verifier)
        self.assertEqual(row['quote_status'], 'VERIFIED_EXECUTABLE')
        self.assertEqual(row['dirty_allowances'], {'SKHYB': 68939879194155372})

    def test_profile_without_per_symbol_approve_gas_is_a_contract_error_even_when_disabled(self):
        from larp.contracts import ContractError
        original = self.verifier(self.records[0])
        broken = profile()
        broken['quote_cost_summary'] = dict(broken['quote_cost_summary'], symbols={})
        with self.assertRaises(ContractError):
            UntrustedQuoteVerifier(original.decoder, broken, wallet=original.wallet, bnb_decimals=18)
