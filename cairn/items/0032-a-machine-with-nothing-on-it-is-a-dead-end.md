---
id: 32
title: A machine with nothing on it is a dead end
type: chore
status: done
milestone: v1.4
assignee: Oddur Sigurdsson
created: 2026-09-21
updated: 2026-09-21
priority: p2
effort: s
area: output
---

## 2026-09-21

On a machine with no developer tooling on it:

     andy  228G volume · 219G used · 9.3G free  █████████████████▎ 96%

      nothing found

That is the whole output. It is also what you get if the scan failed, if the roots were wrong, or if you typo a directory -- four different situations sharing one dead end, three of which have something useful to say.

Proposal. Say which of them it was. No catalog location exists and no roots were found: andy looked and there is genuinely nothing, which is good news and should read as such. Roots were given but hold nothing: name them, since a typo looks exactly like an empty directory. The scan errored: say so, because "nothing found" is a lie in that case. Nothing over the -m floor: say that too, rather than implying emptiness.

Small, and the first thing a new user sees if they are lucky enough to have a clean machine.

Acceptance criteria
- [x] An empty machine reads as a finding, not a failure
- [x] Roots that hold nothing are named
- [x] A failed scan is distinguished from an empty one
- [x] Everything hidden by -m says so and how to see it
