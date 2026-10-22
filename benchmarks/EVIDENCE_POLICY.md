# Evidence gate for ContextForge claims

This is a product quality policy, **not a claim of improved AI performance**.

## Three distinct evidence classes

1. **Mechanics (tested):** Python unit/integration tests and offline recovery
   benchmarks can show that state is stored, retrieved, isolated, and restored
   for specified input cases. CI tests do not measure an agent's decisions.
2. **Observational use (measured):** Real Codex session JSONL can show tool
   use, actual compaction events where recorded, and reported usage. Run
   `python3 benchmarks/trace_diagnostics.py /private/rollout.jsonl`.
   The analyzer emits aggregates only; never upload or commit raw logs.
   A historical session without a paired control cannot establish causation.
3. **Agent efficacy (NOT YET ESTABLISHED):** Requires independently graded,
   paired **actual model executions** on held-out broad tasks. Do not advertise
   fewer mistakes, less token use, better bounties, increased success, or
   superiority to native Codex until this bar is met.

## Experiment design before marketing

- **Baseline:** Native Codex without ContextForge. Verify genuine absence of
  the global skill, AGENTS.md instruction bleed, persistent state and previous
  trials. Same model, reasoning effort, permissions, tools, account conditions
  and task budget. Use separate sandboxes/workspaces.
- **Ablations:** Native; core context/checkpoints; core plus global lessons;
  code-mode orchestration *as a separate variable* only if that question is
  worth investigating. Never change multiple mechanisms and attribute all
  gains to memory.
- **Realistic tasks:** Vetted, externally graded, independently selected
  software regressions (including SWE-bench Pro V2 with integrity checks),
  Terminal-Bench tasks, independent real repository bug fixes, and authorized
  reproducible security labs with hidden seeded weaknesses and sound negative
  controls. No made-to-win synthetic tasks as headline evidence. For bounty
  tasks, assess scope/eligibility and evidence for an actual, independently
  reproduced defect; a successful scan or plausible report is not a success.
  Real wild bug bounty targets lack a known total-vulnerability oracle, so do
  not present them alone as an agent success-rate benchmark.
- **Task quality:** Verify acceptance oracle passes a correct reference
  solution and fails a known incorrect/empty solution. Audit instructions
  against grader; record unsolvable or misleading tasks rather than silently
  excluding bad outcomes. Keep grading state isolated from the agent.
- **Runs:** Preregister a task list, baseline, prompts, policies, randomization
  method, token/time budgets and stopping rule. Multiple seeds and held-out
  tasks; repeat on a different model/period before suggesting transfer.
  Report full denominators and uncertainty, including failures and limits.
  Native session resume, fresh-thread restart, and **observed** automatic
  compaction are different interventions and should be evaluated separately.
- **Outcomes:** Primary = externally verified completion/report validity.
  Secondary = median wall time, reported input/cached/output/reasoning tokens,
  actual model invocations, cost when available, failed actions, repeated
  unproductive work, negative transfer and false-confidence claims.
  Do not infer subscription quota from token totals.
- **Regression gate:** Do not promote a new architecture if it reduces
  verified task completion or creates unacceptable added token/time overhead.
  Where trials are too few to decide, label the feature *experimental* and
  do not market a win. Particularly measure **global lesson negative transfer**.
- **Limitations:** The included `live_codex.py` synthetic telemetry test is
  a smoke test of memory persistence. No fair, broad, paired real-model
  comparative results have yet been published by this repository.

## Public marketing language

Allowed with corresponding evidence:

- "Tested local checkpoint and compaction-state recovery on Python 3.10/3.12."
- "Provides a CLI and optional Codex skill for durable project memory."
- "Recorded actual tool and compaction events in a historical Codex session"
  only when aggregation method and privacy limitations are explained.

**Not allowed before independent real-agent trials:**

- "Makes Codex more accurate / productive / efficient"
- "Finds more vulnerabilities or increases bounty income"
- "Works flawlessly", "prevents reasoning mistakes", or invented win rates
- "Code Mode cuts our tokens by X%" based on other companies' workloads.

## Next genuine decision

If authenticated Codex execution is unavailable, stop at honest mechanical
and trace diagnostics. Never use test code that simply simulates the agent to
invent LLM evidence. When a proper runner is available, freeze the public
benchmark plan before executing the first paired batch. Publish methodology,
graded outcomes, failure cases and whether the conclusion supports keeping
each optional subsystem.
