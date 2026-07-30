# Repository Guidelines

## Project Structure & Module Organization

This repository targets a ROS Noetic robot dog for the RoboCom intelligent-delivery competition. Keep policy documents at the root and future ROS packages under `catkin_ws/src/`.

## Build, Test, and Development Commands

There is no build system, package manifest, or automated test suite yet. Review changes with standard text tools:

```powershell
Get-Content -Raw .\MODEL_ROUTING.md
rg "^#{1,6} " *.md
rg "GPT-5\.6|L0|L1|L2|L3" MODEL_ROUTING.md
```

They inspect content, headings, and terminology. Commit tooling configuration and document reproducible commands here.

## Writing Style & Naming Conventions

Use UTF-8 Markdown and preserve Chinese terminology and numbered headings. Use short paragraphs, ordered procedures, comparison tables, and language-tagged fences. Keep model IDs and labels exact: `gpt-5.6-terra`, `xhigh`, `L2`. Name top-level policies in uppercase snake case, as in `MODEL_ROUTING.md`.

## Validation Guidelines

Preview Markdown and check headings, tables, lists, and code fences. Verify routing tables, escalation rules, contracts, and prompts remain consistent. Update dates only for policy changes. Put future checks under `tests/` or `scripts/`.

## Commit & Pull Request Guidelines

No existing Git convention can yet be inferred. Use imperative commits such as `docs: clarify Terra escalation criteria`. Pull requests should explain affected sections, safety implications, validation, linked issues, and layout screenshots when needed.

## Security & Configuration

Never commit keys, credentials, private prompts, or production data. Treat security and irreversible changes as high risk under `MODEL_ROUTING.md`.

## Agent-Specific Instructions

Any task that writes or modifies source code must use at least one sub-agent for a bounded implementation, test, or review subtask. The primary agent must integrate changes, inspect the diff, run tests, and resolve conflicts. Documentation-only edits do not require delegation. Follow `MODEL_ROUTING.md`; never delegate high-risk decisions solely to a lower-capability model.

## AI Work Records

Use the `project-memory-records` skill for project work. At every new conversation, read `docs/ai-records/CHANGE_LOG.md` and `MISTAKE_LOG.md`; read `FAILED_APPROACHES.md` before choosing a new approach. For source-code work, create or mark a change unit `进行中` and update it to `改动完成` after each completed code change—these are the only permitted statuses. Record reusable mistakes once confirmed. Record a failed approach only when the user says it failed or the work switches approaches.
