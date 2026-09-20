---
id: 8
title: CI on macOS and Linux
type: chore
status: blocked
milestone: v1.1
assignee: Oddur Sigurdsson
claimed: 2026-09-20
depends_on:
- 4
created: 2026-09-20
updated: 2026-09-20
priority: p1
effort: s
area: tests
---

## Problem

Nothing runs the tests but a person remembering to. The Linux work (0007) makes
a claim about a platform the author does not develop on, and an untested claim
is a lie with a delay on it.

## Proposal

One GitHub Actions workflow, `.github/workflows/test.yml`:

- `macos-latest` and `ubuntu-latest`
- Python 3.9 (the floor the README promises) and 3.13
- `python3 -m pytest`
- A smoke run of the real program against a synthetic tree —
  `andy --json <dir>` — asserting it exits 0 and emits parseable JSON, so the
  argument parsing and output paths are covered end to end
- `python3 -m compileall andy` as the cheapest possible syntax gate on 3.9

No linter, no formatter, no coverage gate. The program has a house style that a
default ruff config would fight, and a coverage number is not the problem here.

## Acceptance criteria

- [ ] Workflow runs on push and pull request
- [ ] Both platforms, both Python versions, green
- [x] The 3.9 floor is actually verified rather than asserted in prose
- [x] A badge in the README only once it has been green on main

## 2026-09-20

The workflow is written and its shell step was run for real on both platforms before being committed: locally on macOS with python3, and inside python:3.9-slim and python:3.13-slim containers for Linux. Criteria 1 and 2 stay unticked until GitHub itself runs it — 'the workflow is correct' and 'the workflow is green' are different claims, and only the first is established.

Criterion 3 is the one that paid for the item. Running the suite under Python 3.9 found that andy has never worked on Python 3.9, despite the README promising it since 1.0:

    p(f"   {ink.dim('a running container VM or a network mount will block du; '
                    'stop it, or point andy at that path alone')}")

An expression inside an f-string could not span lines until Python 3.12 (PEP 701). This is a SyntaxError on 3.9, 3.10 and 3.11 — the file does not import at all, so nothing about it is subtle. It was in 1.0, and I reproduced it in the new report wording before finding it. Fixed by building the string above the f-string.

Two smaller things the CI script caught while being written. The first run leaves andy's own cache under ~/.cache, and ~/.cache is a catalog entry, so a second run in the same HOME measures it and the two engines appear to disagree by exactly one 4096-byte block; each run now gets a fresh HOME. And the --commands check greps for any line that is not blank or a comment, which is the only mechanical way to assert the thing the README promises about it.

No badge in the README. It has never been green on main, because it has never run.
