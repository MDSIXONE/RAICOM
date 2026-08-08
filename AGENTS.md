# Universal Rules

- Always answer in Chinese unless the context requires otherwise.
- Do not write defensive or fallback code; it does not solve the root problem. Prefer full exposure: let failures surface clearly (explicit errors, exceptions, logs, failing tests) so bugs are visible and can be fixed at the root cause.
- When editing existing code: if you notice unrelated dead code, mention it - don't delete it.

# Repository Guidelines

## Commit & Pull Request Guidelines

Follow the `github-commit` skill for commit message and pull request conventions. Use one coherent change per commit. Do not rewrite published history merely to restyle messages.

## Security & Configuration

Never commit keys, credentials, private prompts, or production data.

## Agent-Specific Instructions

Any task that writes or modifies source code may use a sub-agent to complete the task.

## AI Work Records

Use the repository `project-memory-records` skill for all project work.