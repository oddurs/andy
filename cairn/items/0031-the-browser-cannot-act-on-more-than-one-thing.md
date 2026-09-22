---
id: 31
title: The browser cannot act on more than one thing
type: feature
status: done
milestone: v1.4
assignee: Oddur Sigurdsson
created: 2026-09-21
updated: 2026-09-21
priority: p2
effort: l
area: tui
---

## Problem

## Proposal

## Acceptance criteria

- [ ]

## 2026-09-21

The browser lets you copy one command at a time. Reclaiming a disk is not a one-command job: the answer is usually four or five directories across three categories, and the only route today is to visit each row, press c, paste, repeat.

Proposal. Mark rows with space, and a key that copies every marked row as one script -- the same script --commands prints, filtered to the selection and with its total. Marks survive filtering and sorting, so the natural flow works: filter to target, mark the ones you mean, clear the filter, filter to node_modules, mark those, then copy once.

The footer carries the count and the total marked, because a person about to paste rm -rf somewhere wants to see what they have selected before they do.

Marking is not deleting and andy still deletes nothing. It is the difference between a tool that tells you the answer and one that hands it to you.

Acceptance criteria
- [x] space marks and unmarks the row under the cursor
- [x] Marks are visible, and survive filtering, sorting and rescanning
- [x] A key copies the marked rows as one commented script, with the total
- [x] The footer shows how many rows and how many bytes are marked
- [x] Marking a group means its members, not a placeholder
- [x] With nothing marked the key says so rather than copying nothing

## 2026-09-21

Space used to expand a branch, alongside enter, tab and right arrow. It now marks, and the other three still expand -- a key that both selects and navigates cannot be the marking key, and enter is the one people reach for to open something.

Marks are held by key rather than by object: a path where there is one, and kind plus label for a group, which has none. That is what makes them survive filtering, sorting and a rescan, and a rescan rebuilding every Node is exactly when you would lose them.

marked_size deduplicates. Marking a group and then something inside it is easy to do by accident, and a footer that added them together would overstate what is about to be reclaimed -- which is the one number a person reads before pasting rm -rf.

Writing this found the browser still copying raw templates. 0029 filled the placeholders in --commands and the clipboard is the same consumer; `c` was putting `rm -rf <path>` on it, which is worse than copying nothing. The detail pane showed the template too. Both now go through the same fill.

And it reintroduced the Python 3.9 f-string bug from 0012, in the 0032 wording -- an expression spanning two lines inside an f-string, which is a SyntaxError before 3.12 and so stops the file importing at all. Caught by the 3.9 CI job, as designed, but it should not have needed CI: there is now an AST test that finds them before the push.
