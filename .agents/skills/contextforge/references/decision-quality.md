# Decision quality: a compact diagnostic, not a mandatory workflow

Use this reference **only** when an agent is wasting effort, repeating attempts,
or coming out of a long interruption with a weak plan. Do not inject it into
every prompt or turn it into a rigid rule engine.

## Reusable distinctions

| What appeared to happen | What was actually demonstrated | Next useful question |
| --- | --- | --- |
| Tool returned success / accepted | A request or operation was accepted | Is the actual downstream goal observable? |
| Test did not find a bug | One tested configuration/path had no demonstrated issue | Which exact boundary did this eliminate? |
| Found a genuine defect | A behavior is reproducible under stated conditions | Does it meet the **user's** acceptance conditions? |
| Repeated promising leads | Many candidates were explored | Are we getting stronger evidence or only more surface changes? |
| Compaction recovery succeeded | The next task can be reconstructed | Was the recovered **strategy** still worthwhile? |
| Another hypothesis written | A possible explanation was added | Which evidence would distinguish it from the alternatives? |

## Cheap gates before expensive effort

First determine whether the candidate meets the objective's **external
acceptance criteria**, when those criteria are checkable. Examples:

- **Research:** Is the source suitable for the question and time frame?
- **Software:** Is this the supported version/target platform? What hidden or
  explicit tests must pass? Does the fix avoid unintended regressions?
- **Authorized security testing:** Are scope, version, reproducibility, impact,
  reportability, and the relevant program's eligibility rules compatible?
- **Operations:** Does the change satisfy the requested service-level outcome,
  rollback requirement and available permissions?
- **Job/workflow search:** Is the option still active, eligible and actually
  relevant before spending time tailoring a complete application?

A candidate can be technically interesting while still failing the user's
win condition. Cheap disqualifiers belong near the beginning; subtle conditions
may be discovered later, and should update the plan.

## Depth, breadth and rabbit holes

Breadth is useful for searching; depth is needed to validate. Neither is always
better. A *repeated strategy* means repeating substantially the same assumption
or test mechanism without changing the evidence that justifies it, even when
the target name, URL, file or hypothesis label changes.

When repeated failures occur: distinguish **failed candidate**, **failed
mechanism**, and **failed selection strategy**. A reasonable response might be
a deeper control test, a different mechanism, or a more appropriate goal;
choose based on evidence, not a fixed retry count.

A promising failed test may justify continuing; a thousand cheap tests may
still provide little information. Do not equate token spend, elapsed time or
number of tool calls with progress.

## Post-compaction continuity

Resume from the *original objective + decisive evidence + why the next action
matters + when to reconsider*. Preserve cross-project reasoning lessons only
when human-reviewed and genuinely transferable. Never use a generic lesson to
override direct current-task evidence or the user's instructions.

## Observable acceptance tests for ContextForge

The skill is useful only when paired-agent trials establish improvement over
a native-agent baseline. Compare no-skill, context-only and context-plus-global
lessons on externally graded long tasks; vary interruptions and distracting
evidence; measure verified completion, false conclusions, redundant operations,
tokens, time, negative transfer and compaction recovery.

A better-looking checkpoint or a persuasive narrative is **not** proof of
improved reasoning. Report regressions and drop optional components if they
cause more errors or context overhead.
