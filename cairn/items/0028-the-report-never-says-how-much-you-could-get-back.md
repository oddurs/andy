---
id: 28
title: The report never says how much you could get back
type: feature
status: done
milestone: v1.4
assignee: Oddur Sigurdsson
created: 2026-09-21
updated: 2026-09-21
priority: p0
effort: m
area: output
---

## Problem

## Proposal

## Acceptance criteria

- [ ]

## 2026-09-21

Every location carries a safety rating -- safe regenerates itself, rebuild costs you a rebuild, review may hold something you want -- and the default report shows it nowhere. You get "20.6G OrbStack" and have to open --tree, -i or --commands to learn whether you can touch it. The rating is decision support printed everywhere except where the decision is made.

The arithmetic is exact once only locations are counted, groups and breakdowns excluded:

    safe        8.2G   20 locations
    rebuild    63.4G  234 locations
    review      8.1G   49 locations
    sum        79.8G  303          == mapped

So the headline andy has never printed is the one its user actually wants: 71.6G is reclaimable, 8.2G of it without thinking, and 8.1G wants a look first.

Proposal. A line under the category table giving the split, and a rating against each row of "largest items" so the list can be read as a plan rather than an inventory. --json gains the same totals.

What to be careful about. "Reclaimable" must not read as "andy will reclaim it", and the sum of safe and rebuild is not a promise -- deleting a rustup toolchain you are using costs more than a rebuild. The wording carries that, and the safety ratings themselves stay conservative.

Acceptance criteria
- [x] The report states the split, and the three parts sum to mapped
- [x] Every row of "largest items" shows its rating
- [x] --json carries the same totals
- [x] Nothing reads as a promise that andy will delete anything
- [x] A test asserts the split equals the mapped total, on a model and end to end
