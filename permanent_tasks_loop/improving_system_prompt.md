Your task is to iteratively optimize an agent's system prompt through repeated benchmark-driven refinement.

Objective:
Improve the system prompt in ways that generalize to real filesystem tasks. Do not optimize for benchmark-specific tricks, case memorization, or narrow gains that are unlikely to transfer.

Loop:
1. Review the results of the most recent run on the handmade benchmark (125 cases).
2. Identify general failure patterns, weak behaviors, or recurring mistakes.
3. Propose one small, targeted revision to the system prompt aimed at fixing a broad failure mode.
4. Reject revisions that appear tailored to specific benchmark cases instead of general behavior.
5. Run the updated agent on the 125-case benchmark.
6. Compare the new result to the previous best result.
7. Keep the revision only if the improvement is meaningful and likely to generalize.
8. Revert the revision if the result is worse, nearly unchanged, or suspiciously benchmark-specific.
9. Log the iteration with:
   - the prompt change,
   - the reason for the change,
   - previous score,
   - new score,
   - keep/revert decision.

Rules:
- Optimize for generalization, not benchmark exploitation.
- Prefer minimal, interpretable edits over large rewrites.
- Do not encode benchmark-specific solutions.
- Be conservative about accepting changes.
- Maintain a history of accepted and rejected revisions.

Repeat the loop until explicitly stopped.

Stopping rule:
- If execution is stopped between iterations, keep the last validated prompt.
- If execution is stopped in the middle of an iteration, discard any unevaluated prompt change and revert to the last validated prompt.

