---
id: 3
title: Nested sizes double counted when a sibling sorts between parent and child
type: bug
status: done
milestone: v1.1
assignee: Oddur Sigurdsson
created: 2026-09-20
updated: 2026-09-20
priority: p0
effort: s
area: model
---

## What happens

`Model.recompute()` subtracts an inner measurement from its enclosing one by
sorting every measured path lexicographically and walking a stack:

```python
for n in sorted(measured, key=lambda n: n.path):
    while stack and not n.path.startswith(stack[-1].path + os.sep):
        stack.pop()
```

That assumes a parent is never separated from its own descendant in the sort.
It is, whenever a sibling's next character sorts below `/` (0x2F) — `-`, `.`,
`+`, a space. `~/.cache-v2` sorts *between* `~/.cache` and `~/.cache/uv`, so the
sibling pops the parent off the stack and the child is attributed to nothing.

The parent then keeps bytes that are also listed on their own, and the category
total counts them twice.

## What should happen

The inner measurement is subtracted from the nearest enclosing measured path,
whatever the siblings happen to be called. From the README, "Notes":

> **Sizes don't double count.** When one measured location sits inside another,
> the inner one is subtracted from the outer.

That is the invariant, and this breaks it.

## Reproduction

```python
parent = Node(label="parent", path="/x/.cache",    measured=1000)
child  = Node(label="child",  path="/x/.cache/uv", measured=400)
sib    = Node(label="sib",    path="/x/.cache-v2", measured=50)
# sorted order: /x/.cache, /x/.cache-v2, /x/.cache/uv
```

Observed: `parent.inner == 0`, `parent.size == 1000`, category total `1450`.
Expected: `parent.inner == 400`, `parent.size == 600`, category total `1050`.

## Proposal

Sort on the path's components rather than its bytes — `n.path.split(os.sep)` —
which orders a directory immediately before everything beneath it whatever its
siblings are named. One line; the stack walk is unchanged.

## Notes

It does not fire on the author's machine today: none of the 285 paths andy
measures there interleave. Latent, not theoretical — the catalog already pairs
`~/.cache` with several `~/.cache/*` entries, and any tool that drops a
`~/.cache-<something>` beside them sets it off.

## Acceptance criteria

- [x] `recompute()` orders measured paths by component, not by byte
- [x] A regression test covers the interleaved-sibling case above
- [x] A property test asserts the invariant directly: for every measured node,
      `inner` equals the sum of the measurements nested under it

## 2026-09-20

Fixed in andy:666 by sorting on n.path.split(os.sep) instead of n.path, with the reasoning in a comment above the loop so the next person does not 'simplify' it back.

Covered three ways in tests/test_model.py: the exact repro from this item, a sweep over every character that sorts below os.sep (' !"#$%&'\''()*+,-.'), and a 300-trial property test that checks the invariant directly against an independently computed nearest-ancestor map. The property test found two bugs in itself before it found none in andy, which is the right ratio.
