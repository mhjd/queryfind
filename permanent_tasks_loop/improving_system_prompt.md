Your task is to iteratively optimize an agent's system prompt through repeated benchmark-driven refinement.

Objective:
Improve the system prompt in ways that generalize to real filesystem tasks. Do not optimize for benchmark-specific tricks, case memorization, or narrow gains that are unlikely to transfer.

Benchmark target:
- Use only the handcrafted 125-case benchmark in `benchmark_fs/handmade100_manifest.json`.
- Use only `glm-4.7-flash:latest` for benchmark acceptance decisions.
- Do not use other models to decide whether a prompt revision is accepted or rejected.
- You may use a small representative GLM subset as a cheap screening step, but every accepted revision must also beat or clearly justify itself against the last validated full 125-case GLM run.

Loop:
1. Review the results of the most recent full GLM run on the handmade benchmark (125 cases).
2. Identify general failure patterns, weak behaviors, or recurring mistakes.
3. Propose one small, targeted revision to the system prompt aimed at fixing a broad failure mode.
4. Reject revisions that appear tailored to specific benchmark cases instead of general behavior.
   - Phrase revisions in general search-behavior terms, not benchmark-specific file types, folder patterns, entity categories, or corpus artifacts.
   - Do not mention concrete structures such as hidden maps, directories, incident reviews, customer indexes, vendor cards, or similar benchmark-shaped examples inside the prompt revision.
5. Optionally run the updated agent on a small representative GLM subset to screen out obviously bad revisions.
6. If the subset result is promising, run the updated agent on the full 125-case GLM benchmark.
7. Compare the new full-run result to the previous best full GLM result.
8. Keep the revision only if the improvement is meaningful and likely to generalize.
9. Revert the revision if the result is worse, nearly unchanged, or suspiciously benchmark-specific.
10. Log the iteration with:
   - the prompt change,
   - the reason for the change,
   - previous full GLM score,
   - subset score if used,
   - new full GLM score,
   - keep/revert decision.

Rules:
- Optimize for generalization, not benchmark exploitation.
- Prefer minimal, interpretable edits over large rewrites.
- Do not encode benchmark-specific solutions.
- Do not encode benchmark-specific vocabulary, document classes, or filesystem structures in the prompt.
- Be conservative about accepting changes.
- Maintain a history of accepted and rejected revisions.
- If a screening subset is used, choose cases that reflect a real failure pattern rather than a hand-picked easy win.

Repeat the loop until explicitly stopped.

Stopping rule:
- If execution is stopped between iterations, keep the last validated prompt.
- If execution is stopped in the middle of an iteration, discard any unevaluated prompt change and revert to the last validated prompt.
