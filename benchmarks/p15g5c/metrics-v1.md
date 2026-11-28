# LNZ P1.5g.5c.3 — Metrics v1
Companion to preregistration-v1.json, commit f7ee4c4dd8fe3b89ad9dea58b487abacc9f88cae.
Status: preregistered, not executed.

## Primary metrics
- Positive coverage: attempted positive targets / 10.
- Positive acceptance: distinct positive targets with an accepted root proof / 10 (unsupported and unattempted remain in denominator).
- Conditional acceptance: accepted positive targets / attempted positive targets.
- Negative false acceptance: distinct validated false targets with any accepted root proof / number of validated false targets attempted; also report coverage / 10.
- Immediate repair: genuine Lean proof failures followed by an accepted proof of the same target at the next model attempt / genuine Lean proof failures followed by a model retry. Report separately the count of failures without retry and the fraction repaired eventually within budget. No scripted failures, policy rejections, timeouts or unavailable executions in the genuine Lean failure category.
- Attempts: count every provider call, including invalid output, repeated proof, and provider failure; report Lean executions separately. Report per-target values and totals, not only successful cases.
- Lemma discovery: count distinct model-generated, independently checked auxiliary lemmas actually used by an accepted root proof; report targets with at least one such lemma / 10. Preexisting library lemmas do not count.
- Wall time: elapsed monotonic time from target start to terminal outcome, including generation, queue and recovery. Record Lean execution and provider time separately when measurable.
- Cost: record actual provider tokens and billed amounts when exposed, runner seconds and actual billed amount when available. Missing values are null, not zero. No invented conversion rates.
- Baseline: independent single-tactic simp, omega, decide runs for each target; same context and Lean version, 120 s each. Report separate results and costs, never credit baseline success to AI.

## Evidence and stop conditions
Record model/version as exposed, worker commit, Lean version, context and statement hashes, candidate hash, raw provider output, Lean diagnostic, exit code, axiom audit, timestamps, request and receipt identifiers, terminal status. Distinguish runner acceptance from independent attestation.
Four provider calls total per target, including lemma-generation calls; four candidate auxiliary lemmas maximum; 120 seconds per Lean invocation, 900 seconds total per target. Baseline runs are separate from the model budget. No retry after budget expiry. Stop and investigate any accepted validated false target.
Do not send evaluator counterexamples or negative-control labels to the model. No expected proof in prompt. Fixed target order B01 through B10, positive then negative. Do not omit failures. Any change to definitions, budgets or scoring after first execution requires a new version and separate reporting.
Before benchmark execution, elaborate all contexts and both statements in Lean without proving the target, and validate negative counterexamples separately. The current restricted grammar and registered-target worker are not yet sufficient for all tasks. Report NOT RUN until this gate is met.
