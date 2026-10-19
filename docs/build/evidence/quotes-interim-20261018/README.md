# Interim quote handoff — KMP-QUOTE01

Snapshot at 2026-10-18 ~06:58 UTC, for Isaac's router review (#118/#119/#120).
This is observed quote data, not realised fills, a final profile or signing approval.
User-authorized sanitized export; no `.env`, keys, signing or ai-seeds credentials.

| Evidence | SHA-256 / coverage |
|---|---|
| Original private transport archive | `d2127481bd8835a1f6f12abcaae5a39ed961c521c07ad1a49567c3de729e9520` (298,429 bytes, 29 data files plus manifest; analysis/README added after transfer) |
| [Snapshot manifest](manifest.json) | `b6db3560fdbfd2e7f6b2fba70ddd6c99927567642b2edf95e95a7ba6b4e5a1b4` |
| [Offline coverage](coverage.json) | `1aac4be95d68dbc2e2c16bdfa902cb28beec9f4559a24b261e7650ae3a8a23df` |
| Capture implementation | pushed integration `eda2ed2ab1ab4b72f220eb6b92e882737d950825` |
| Actual observations | Oct16 18:19:09.205–Oct18 06:56:06.986 UTC; 1,021 records: 850 token samples, 170 BNB prices, one recorded failed round |
| Each of five tokens | 170 samples; 9 US_SESSION /161 OFF_SESSION; Oct16/17/18, including weekend; all recorded `token_open:true` |
| Gas | Both swap-gas estimates use FALLBACK for every sample (1,700 estimates); not measured swap gas or final signer-cap proof |

The three JSONL files are complete snapshots, with no partial trailing lines.
The 26 `selected-raw` files are the exact referenced response artifacts for the
latest successful sample of each of five tokens. All manifest file hashes and
lengths verified after transfer. **This is not the complete historical raw store.**
Older referenced raw files remain in the original private capture store; request
specific hashes for further route investigation. Raw responses preserve unsigned
route data, public wallet and request observations. Public address is not a key.
Both stored Web3 credentials were screened remotely in literal/encoded data and
decoded response bodies before export; no values were printed or exported.

No continuous-availability claim is made: the user clarified that earlier data
were interim capture data. There is a measured ~4h24m gap between the last
pre-failure successful token samples and the resumed samples; see per-token
endpoints in coverage.json. `tmux 1:0.0` was inspected: its surviving process was
`systemd-inhibit`/sleep, which kept the host awake but was not a quote collector.

The earlier capture exited on `authentication_error`. The underlying saved
response `1a6615b5280898e2c98062212a25d0d7000fc178830d9143525383c876850d9d`
was HTTP401/code40103, “Timestamp outside recv_window”: request timestamp
02:42:13.154Z; serverTime02:42:18.219394497Z; response02:42:18.257Z (~5.1s).
That demonstrates request freshness rejection, not invalid keys. NTP was
synchronized. A fresh read-only token-list preflight succeeded HTTP200 in552ms
with the same privately stored Web3 key pair (artifact
`9540573d5fe3d834e18f7fadb4ce33e823b8184fb7674186902ccf554cafc94a`).

The unchanged committed runner resumed at **Oct18 06:54:40 UTC**, process106610,
configured to stop **Oct20 00:00 UTC**. Two completed resumed rounds at06:54:40
and07:06:06 have five token samples/zero failures each (log uses round-start
time). Originals/logs were preserved. The second round is after this snapshot.
The configured600s delay is after each round, so actual spacing is about11m27s,
not exactly10min. Continued future operation needs health checks; an alive sleep
inhibitor alone is insufficient. No timestamp window or authentication guard
was weakened; no credentials rotated or account settings changed.

Default offline `summarize` was run on this exact snapshot with10 samples per
token/regime,3 UTC days and weekend required. **REFUSED:** all five have only9
US_SESSION samples. No lowered flags, final summary/profile or pin was produced.
The next regular session on Oct19 can supply coverage if capture remains healthy.

The older PC-AWS07 interim profile has recorded parameters `--min-days 2
--min-samples 9` and reported file SHA
`d951207f432879eda6b349ae334104e47803f809eb5e94aef422c2e31cab4542`.
Its summary is only recorded by prefix `41e17b4d…` in IDEA-066; its exact prior
capture hash/full summary bytes were not available here and were not reconstructed
from this later snapshot. Yao/Keith must retain that original evidence; this
handoff does not retroactively give it default three-day/ten-sample acceptance.

Fee caveats from merged FN-02 remain: historical SAMPLE records have no
`fee_observations`; raw latest buy/sell/requote responses retain the fields.
`tradeFee` is documented as a network-fee estimate, not a route-fee rate;
route-fee inclusion remains UNVERIFIED (#119). Quotes use40USDT, above the
candidate development signer's35USDT input cap, and are not proposed trade sizes.
Isaac/Keith review after final coverage; no router/deadline/cap qualification is
implied by delivering these artifacts.
