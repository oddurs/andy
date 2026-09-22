---
id: 35
title: The path column repeats the label instead of completing it
type: feature
status: done
milestone: v1.5
assignee: Oddur Sigurdsson
created: 2026-09-21
updated: 2026-09-21
priority: p1
effort: s
area: tui
---

## Problem

## Proposal

## Acceptance criteria

- [ ]

## 2026-09-21

At 120 columns the browser prints:

    rsst/target                ~/Code/rsst/target
    poptop/target              ~/Code/poptop/target
    cairn/target               ~/Code/cairn/target

The label of a project artifact is its path relative to the scan root, so the
path column is the label again with a prefix. Thirty-eight columns spent
restating what is already on the row, on every row, while the labels beside
them are being trimmed to fit.

Proposal. Print the part the label does not carry, and only that -- the root
the thing was found under:

    rsst/target                ~/Code
    poptop/target              ~/Code

Which is genuinely informative when several roots are configured, and quietly
disappears into a narrow repeated word when only one is. Where the label is not
a tail of the path -- a catalog entry like "pnpm store" -- the whole path is
still the useful thing and is still what gets printed.

Acceptance criteria
- [x] A path column never repeats what the label already says
- [x] A label that is the tail of its path leaves only the prefix showing
- [x] A catalog location still shows its whole path
- [x] Nothing is lost: the detail pane still shows the full path

## 2026-09-21

Sizing the column to its contents turned out to matter more than the change itself. The path column was a fixed third of the available width, which was defensible when it held a whole path and absurd once it held `~/Code`: thirty-eight columns of air while the labels beside it were being trimmed. It is now as wide as the widest path text among the rows actually on screen, capped, and the labels get the rest -- which is why `.worktrees/nun/feat/0030-multi-cursor/target` now fits where it used to be elided.
