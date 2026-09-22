---
id: 30
title: Paths are elided where the information is
type: bug
status: done
milestone: v1.4
assignee: Oddur Sigurdsson
created: 2026-09-21
updated: 2026-09-21
priority: p1
effort: s
area: output
---

## What happens

## What should happen

## Reproduction

1.

## 2026-09-21

shorten() keeps the first third and the last two thirds of the available width and drops the middle. For a sentence that is fine. For a path the middle is the part that identifies it, and the head is a prefix shared with everything else on screen.

From the browser, at 118 columns:

    halide-theme/.claude/…/instrument/node_modules    ~/Code/ha…ument/node_modules
    halide-theme…claude/…/print-sheet-ui/node_modules ~/Code/ha…et-ui/node_modules
    halide-theme/.claude/…/fonts/node_modules         ~/Code/ha…fonts/node_modules
    ruthless/brevity/target                           ~/Code/ru…ess/brevity/target
    stable-aarch64-apple-darwin                       ~/.rustup…rch64-apple-darwin
    1.98.1-aarch64-apple-darwin                       ~/.rustup…rch64-apple-darwin

Four problems in six lines. The path column is a worse copy of the label, which for a project artifact already is the path. The rustup rows differ only in a part the elision removed, so eight toolchains read as eight copies of one row. Labels get elided twice, `halide-theme…claude/…/print-sheet-ui`, which is two different ellipses meaning two different things. And `~/Code/ha…ument/node_modules` has thrown away every directory that identified the project while keeping the two that did not.

Proposal. Elide paths by whole segments rather than by characters, keeping the last two -- the ones that name the thing -- and as many leading segments as fit: `~/Code/…/instrument/node_modules`. project_label already does something like this and should be the shared implementation.

In the browser, drop the path column when it would only restate the label, and for an itemised child show nothing: its label is its basename and its parent is the row above.

Not cosmetic. Eight rows that cannot be told apart is a functional failure in a program whose job is telling you which one is big.

Acceptance criteria
- [x] Paths elide by segment, keeping the identifying tail
- [x] Two paths differing only in a middle segment render differently
- [x] A label is never elided twice
- [x] The browser does not print a path that restates the label
- [x] Output still fits the width exactly, at every width

## 2026-09-21

Criterion 4 needs a word. An itemised child no longer prints a path -- its label is its basename and its directory is the row above -- and that was the case the item was written about. A project artifact still does: its label is the path relative to a scan root, so the column adds which root it was found under, and with several roots configured that is the only thing distinguishing two identically named projects. Restating and completing are different, and only the first is worth removing.

project_label no longer trims. It is the label the report, the browser, --json and --commands all use, and how much of it fits is a question about the column it lands in. Trimming it there as well is what produced halide-theme...claude/.../print-sheet-ui/node_modules: two ellipses, one from the model and one from the renderer, meaning two different things.

The algorithm prefers the tail over the head, which took a second pass. Keeping the leading segment first gave .worktrees/.../target for a path whose only distinguishing part is the branch name in the middle -- technically an elision, practically the same failure as before. Now the lead is kept only when the tail already fits.
