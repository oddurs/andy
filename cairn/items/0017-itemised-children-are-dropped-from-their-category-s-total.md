---
id: 17
title: Itemised children are dropped from their category's total
type: bug
status: backlog
milestone: v1.2
created: 2026-09-20
updated: 2026-09-20
priority: p0
effort: s
area: model
---

## What happens

`Model.recompute`'s roll-up loses the bytes of any measured node that has
itemised children:

```python
if node.measured is not None:
    node.size = max(0, node.measured - node.inner)
...
return 0 if node.informational else node.size
```

`inner` is the children's measurements, already subtracted so nothing is
counted twice. But the value *returned to the parent* is then only the
remainder — and for a location whose children itemise all of it, the remainder
is zero. The children's bytes are never added to the category.

Latent until 0016 was fixed, because no itemised children existed to lose.
With them present: `rustup toolchains` measures 6.6G, `inner` is 6.6G, so its
row reads `-` and its category reads 778M instead of 7.4G.

`print_tree` then compounds it. A parent below the `-m` floor is skipped with
`continue`, which skips the recursion too, so the children vanish from the
tree as well as from the total.

## Proposal

A measured node's row should show everything underneath it, and it should
contribute that to its parent:

```python
own = max(0, node.measured - node.inner)   # not already itemised below
node.size = own + sum(contributions)
```

`inner` takes the children out, `contributions` puts them back — net
`measured`, which is the invariant, and the tree still shows the breakdown.

That makes a location and its breakdown both non-zero, so "largest items"
would list `rustup toolchains` *and* each toolchain inside it. An itemised
child is a breakdown of a location, not a location of its own; mark it and
exclude it from the count and from "largest items", while keeping it in the
tree and the map where it is the point.

## Acceptance criteria

- [ ] A measured node's size includes its itemised children
- [ ] No byte is counted twice: the category total is unchanged by itemisation
- [ ] `--tree` shows a breakdown even when the parent's own remainder is zero
- [ ] "largest items" lists locations, not their breakdowns
- [ ] A test pins the roll-up against itemised children
