For now, don't pay attention to the benchmark side of the project, and focus on making it work on macOS. These two point will be handled later.
# Reliability
- Choose the most reliable option, prioritizing correctness, reproducibility, and low risk.
- Run and fix code until it works, except when execution is costly (for example API calls). In that case, validate on a small subset first before scaling.
- Commit working changes. Before risky refactors, commit first so rollback is easy.
- Never expose secrets or API keys.
- Default to isolated environments and pinned versions for dependencies and runtimes.

# Logs
- Long-running or critical paths must produce clear logs so progress and failures are visible.
- Prefer timestamped logs with levels such as INFO, WARN, and ERROR.
- Log milestones, progress, failures, and a final summary with key metrics.
- When useful, log both to stdout and to a file.
- Avoid noisy library logs by default, but keep them easy to enable.

# Project files
## PROJECT.md 
Explain the project.

## ARCHITECTURE.md
Keep a concise map of the codebase and the role of each important file/folder.
Update it when files are added, moved, removed, or when responsibilities change significantly.

## STATE.md
Maintain the current status, active tasks, next steps, and enough context for another agent to continue the work.

## PROGRESS.md
Append significant progress and important findings only. Never rewrite history.

## Makefile
Keep all important project commands here, each with a short description.
Update it whenever a script is added, removed, or its interface changes.

## README.md
Keep the top-level `README.md` concise and user-facing.
Update it whenever setup requirements, installation steps, primary commands, default usage patterns, or user-visible behavior changes.
The README should explain:
- what the project is useful for
- the minimum install requirements and setup steps
- the main ways to run it
Do not turn it into an internal design document; keep architecture details in `ARCHITECTURE.md` and product scope in `PROJECT.md`.
