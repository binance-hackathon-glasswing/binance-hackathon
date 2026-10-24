# LD14 — interim rehearsal operations values and measurement plan (LD14-I01, 2026-10-21)

Status: **interim values for the signed development rehearsal only, prepared under Keegan's delegation.** The final
LD14 values (installed at LD24) remain **Isaac's decision** under PF-08 once the measurements below exist. Nothing
here changes a config or host; these are the values to put in the rehearsal's `runtime.json` at LD16/LD17.

Why interim: PF-08 and C05-RV01 keep the exact watchdog, memory and delivery-age values MISSING_MEASUREMENT, and do
not adopt the historical 600 s, 2 h or sum-of-`MemoryMax` examples. Real ACK latency and per-unit RSS are
unmeasured (LD12-M01-RV01). But the runtime refuses a dev or live run without `cycle_timeout_seconds`, so the
rehearsal needs a reasoned value now. The rehearsal itself then supplies the measurements.

## Values

| Setting | Interim value | Derivation (inputs cited) |
|---|---:|---|
| `cycle_timeout_seconds` (runtime watchdog, #35) | **300** | Worst legitimate cycle = the DEV-22 assessment bound (180 s) + the measured non-assessment part of a cycle (max 16.3 s, p95 10.3 s, 70 rounds; LD12-M01 packet) = 196 s. × 1.5 margin = 294 s, rounded up to 300 s. |
| `delivery_age_halt_seconds` (D-DN-04 guard) | **600** | Normal positive-ACK path = uploader poll 5 s + one request at the 15 s socket timeout + one transient retry (`retry_ms` 30 s) + the retried request (15 s), plus one complete-cycle allowance (300 s, above) = 365 s. × 1.5 margin ≈ 548 s, rounded up to 600 s. That is about 1/12 of the shortest window to the hard deadline (a log just before 00:00 UTC must be ACKed by 02:00 UTC: `UPLOAD_GRACE_MS` = 2 h). |
| `MemoryMax` per unit | **unchanged** (runtime 1 GiB; evidence, uploader, execution, archive 512 MiB; signer 256 MiB on its own host) | No measurement supports a change. The 43.6 h unsigned trial ran with these limits and the journal shows no OOM or watchdog lines (LD12-M01). |

The delivery-age value lands near 600 s by derivation; it is not the historical example. The request-time term is
an assumption: the 15 s socket timeout bounds each read, not the whole request, and the next section measures it.

**Known risk, unchanged:**
- The `primary` unit limits add up to 3 GiB on a 2 GiB host with no swap.
- The signed rehearsal also runs `larp-execution`, which the trial never ran.
- Host-level memory pressure is therefore possible even if each unit stays under its own limit.

This is the reason for the RSS sampling below. A measured shortfall needs a reviewed reduction of work or a sizing
decision, not a silent change of limits (PF-08).

## Measurement plan (during LD19/LD21, read-only)

| What | How | Decision rule (PF-08) |
|---|---|---|
| Positive-ACK latency | **New in this change:** the uploader journals one `delivery_attempt` line per chunk attempt, with event, chunk, attempt, HTTP code, outcome, `duration_ms` and wall time (no payload or secret). Read `journalctl -u larp-uploader`. | B = worst normal ACK tail (round log time → ACK of its last chunk) + one complete-cycle allowance, plus a documented margin, and well under the 2 h deadline window. |
| Cycle and drain time | Round start → decision → log from the journal (read-only SQL, as in LD12-M01), plus the execution service's command → final-receipt times on signed rounds. | Watchdog = worst legitimate cycle (including signed-path stalls seen in drills) × margin. Never restart healthy bounded work. |
| Per-unit memory | Read `systemctl show -p MemoryCurrent` for every LARP unit every 60 s across the rehearsal (read-only SSM sampling) and record peaks. systemd 252 keeps no peak. | The smallest limit that passes the worst observed simultaneous peak with documented headroom. If the sum of peaks threatens host RAM, reduce work or make a sizing decision. |
| Restart and disk growth | `NRestarts`, OOM and watchdog journal counts, and data-directory and database size at the start and end of each rehearsal day (as in LD12-M01). | Record the trend; unbounded growth blocks LD24. |

Isaac records the final values with these measurements before LD24. Until then the interim values above apply
only to the development rehearsal.
