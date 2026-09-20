---
id: 16
title: 'Itemised children have never appeared: expand globs are not expanded'
type: bug
status: done
milestone: v1.2
created: 2026-09-20
updated: 2026-09-20
priority: p0
effort: s
area: catalog
---

## What happens

`Spec.expand` is a glob that itemises a location's children — the individual
rustup toolchains, each simulator device by name, each JDK, each Playwright
browser build. `S()` calls `os.path.expanduser` on `path` and not on `expand`,
and `glob.glob` does not expand `~` itself. So the glob is literally
`~/.rustup/toolchains/*`, matches nothing, and the feature has silently done
nothing since 1.0.

20 of the 21 specs that use `expand` are affected — every one written with a
`~`. The only one that worked is the simulator runtimes entry, which starts at
`/Library`.

The `namer="simulator"` code reads `device.plist` to show a simulator as
`iPhone 17 · iOS 26 0` instead of a UDID. That has never run either, and the
README advertises it: "simulator devices (named, not just UDIDs)".

## Reproduction

```python
[s for s in CATALOG if s.expand and s.expand.startswith("~")]   # 20 of 21
glob.glob("~/.rustup/toolchains/*")                             # []
```

## Proposal

Expand `expand` in `S()`, beside `path`, where every other path normalisation
already happens.

## Acceptance criteria

- [x] Every `expand` glob is expanded before `glob.glob` sees it
- [x] Itemised children appear for locations that have them
- [x] Simulator devices are named from `device.plist`
- [x] A test asserts no spec's glob starts with `~`

## 2026-09-20

Found sideways. Fixing 0010 meant running expanduser over the expand glob as well as the path, and the next scan grew six new rows and lost eight gigabytes -- which is how I learned the feature had never run, and then that the roll-up could not cope with it (0017).

20 of the 21 specs using expand were written with a tilde, and glob does not expand one. So every per-toolchain, per-browser, per-JDK and per-simulator breakdown has been dead since 1.0, including the device.plist naming the README advertises as "simulator devices (named, not just UDIDs)". The only one that worked starts at /Library.

A test now asserts no spec glob starts with a tilde, and another builds a tree the glob matches and checks it splits.
