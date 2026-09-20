---
id: 8
title: CI on macOS and Linux
type: chore
status: done
milestone: v1.1
assignee: Oddur Sigurdsson
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

- [x] Workflow runs on push and pull request
- [x] Both platforms, both Python versions, green
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

## 2026-09-20

Green on GitHub, both triggers, run 35517574090 (push) and 35517575776 (pull_request): macos-latest and ubuntu-latest, Python 3.9 and 3.13, plus the clipboard job.

The first run failed, which is the best thing it could have done. The Ubuntu runner has a docker daemon with images loaded, and on Linux andy counts what "docker system df" reports because there is no VM disk there to duplicate -- so a test that built its own temp tree and asserted the total was under 20M measured the runner instead and saw 1.89G. Correct behaviour, badly isolated test, and invisible on macOS where those rows are informational. Nothing but a Linux machine with a live daemon would have shown it; no container I ran had one.

The clipboard job passed all four of its cases on the real runner: xclip under Xvfb, xsel with xclip hidden, wl-copy on headless sway, and clip() returning False with nothing installed.
