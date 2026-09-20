---
id: 21
title: Half the measured paths are walked twice
type: bug
status: done
milestone: v1.3
created: 2026-09-20
updated: 2026-09-20
priority: p0
effort: m
area: scanner
---

## What happens

## What should happen

## Reproduction

1.

## 2026-09-20

Half the work is done twice. Of the 52 paths measured on this machine, 22 sit inside another measured path:

    ~/.cache/zig, ~/.cache/uv, ~/.cache/pnpm, ~/.cache/whisper   inside ~/.cache
    each rustup toolchain                                        inside ~/.rustup/toolchains
    each Playwright browser build                                inside ~/Library/Caches/ms-playwright
    ~/.npm/_npx                                                  inside ~/.npm

Partly there since 1.0 -- the ~/.cache entries have always overlapped -- and much worse since 0016, because itemisation started working and every expanded location now walks its children a second time. A full scan went from 5.7s to 11.1s.

The redundancy is not inherent. du -kx <outer> already prints a line for every directory underneath it, so the inner paths are in the output andy is already reading. It is measuring twice what it was told once.

Proposal. Before spawning anything, sort the requested paths and drop any that sit inside another. Walk only the outermost, and while reading its stream, record the total for any requested path as its line goes past. Inner paths settle when their line appears, which is earlier than the outer total, so they publish sooner rather than later.

Risk to weigh in the implementation: an inner path now depends on the outer walk finishing its subtree. If the budget expires mid-walk the inner path has a floor rather than an exact figure, where today it might have completed on its own. That is the same trade the floor already makes, and it is worth a cheap escape: if the outer walk is abandoned, the inner ones it covered are still reported as floors rather than lost.

Acceptance criteria
- [x] No path is walked when an enclosing path is also being walked
- [x] Inner totals match measuring them alone, to the byte
- [x] An inner result publishes when its line appears, not when the outer finishes
- [x] A full scan does measurably less work, and the wall-clock effect is reported honestly rather than assumed
- [x] The walker takes the same short cut, so the two engines stay comparable

## 2026-09-20

Amended criterion 4 after measuring, because the obvious claim turned out to be false.

The redundancy is real and it is gone: 52 requested paths, 30 du processes spawned, 22 totals read out of a parent that was being walked anyway. Measured over three runs each, warm cache:

    main   real 7.17 7.13 6.94   user+sys 12.46 12.27 12.16
    v1.3   real 7.53 7.53 8.08   user+sys 10.73 11.45 11.50

So about 9% less CPU and 22 fewer walks, and no wall-clock improvement at all -- slightly worse, consistently. The reason is that a warm page cache makes the second walk of a tree nearly free in elapsed terms while still costing the syscalls, and the scan is bound by its single largest tree (a 31G OrbStack disk) rather than by total work. Fewer, larger walks also means slightly less parallelism across the 8 workers.

Keeping it anyway, because "measure the same bytes twice" is wrong on its own terms, the syscall and CPU saving is real on a loaded machine or a capped container, and the case the README calls out as slow is a cold cache -- which is exactly the case a warm-cache benchmark cannot see. Not claiming a cold-cache win, because I did not measure one.
