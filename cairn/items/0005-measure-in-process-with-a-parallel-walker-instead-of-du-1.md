---
id: 5
title: Measure in process with a parallel walker instead of du(1)
type: feature
status: done
milestone: v1.1
assignee: Oddur Sigurdsson
depends_on:
- 4
created: 2026-09-20
updated: 2026-09-20
priority: p1
effort: l
area: scanner
---

## Problem

Every size andy reports comes from batched `du -skx` subprocesses. That works,
and it has three costs.

**It cannot stream.** `du -s` prints one line per argument when that argument is
finished. A 7 GB `target` directory is silence for a second and then a number.
The interactive view advertises that "sizes stream in as they are measured", and
what actually streams is whole directories completing, in batches of up to 96.

**A timeout throws the work away.** When the cap expires, everything `du` had
walked but not finished is lost. The user is told "not measured" for a directory
andy had already counted 20 GB of. The README has to explain this.

**It is slower than it needs to be on the trees that matter.** `du` is one
process per batch, walking depth-first, single-threaded. The directories that
dominate a developer's disk are the file-count-heavy ones — package stores,
`node_modules`, toolchains — and those parallelise well across subdirectories.

Measured on the author's machine, warm cache, against a walker using
`os.scandir` and `st_blocks * 512`, eight threads:

| tree                       | `du -skx` | scandir x1 | scandir x8 |
|----------------------------|-----------|------------|------------|
| `~/Code/rsst/target` 7.5G  |   0.73s   |   1.24s    |   0.99s    |
| `~/.rustup/toolchains` 6.6G|   2.74s   |   1.92s    |   1.43s    |
| `~/Library/pnpm/store` 2.4G|   3.01s   |   1.34s    |   1.02s    |

All three agree with `du` to the byte. Fewer, larger files (`target`) lose a
little to interpreter overhead; many small files win roughly 3x. Cold cache is
I/O bound and should favour the parallel walk further.

## Proposal

Replace `du_batch` with an in-process walker, keeping du's semantics exactly:

- **`st_blocks * 512`**, not `st_size` — allocated blocks, which is what `du -k`
  reports and what "free space" responds to. Sparse container disks depend on it.
- **One filesystem** — compare `st_dev` against the root's, which is `-x`.
- **No symlink following**, and the link's own blocks counted, as `du` does.
- **Hardlinks counted once per walk**, by inode, for inodes with `st_nlink > 1`.

What it buys beyond speed:

- **Partial totals published as it goes.** A node's size climbs while it is
  being walked, so the tree is informative immediately instead of after.
- **A timeout keeps its work.** When the deadline expires, what was counted is
  reported as a floor — "at least 20.1G" — rather than discarded. This is
  strictly better than "not measured" and should be reflected in the UI, the
  JSON (`complete: false`) and the README.

## Risks

A blocked `os.scandir` cannot be cancelled the way a subprocess can be killed.
A worker stuck on the I/O of a running container VM stays stuck for as long as
the kernel takes.

That rules out `ThreadPoolExecutor`: its workers are non-daemon and its
`atexit` hook joins them, so one wedged thread would hang the process on the
way out. Use plain `threading.Thread(daemon=True)` workers and a work queue,
and let the scan abandon a wedged worker instead of waiting for it. Quitting
andy must never wait on a directory.

Keep `du_batch` in the file, unused by the default path, until the walker has
run against a machine with an active OrbStack VM and a network mount.

## Acceptance criteria

- [x] Walker agrees with `du -skx` to the byte on a synthetic tree containing
      sparse files, hardlinks, symlinks and a nested mount point
- [x] Sizes climb visibly during a scan rather than appearing all at once
- [x] A deadline yields a partial floor, flagged as incomplete, never a zero
- [x] Wedging a worker does not delay `q` in the TUI or process exit
- [x] Measured no slower than today end to end on a cold cache
- [x] README's "first run is slow" and "nothing is allowed to hang" notes
      rewritten to describe what the program now does

## 2026-09-20

Built, then rebuilt on evidence. The benchmark in this item was wrong, and the mistake is worth recording: it compared a parallel in-process walker against a single serial du process. Once du was given the same parallelism andy actually uses, du won and kept winning -- on macOS it walks directories with getattrlistbulk, and eight C processes have no GIL to take turns with. More walker threads made it worse (8 threads 6.7s, 16 threads 8.6s, 32 threads 13.2s on the same 263 directories), which is what GIL contention looks like.

So the engine is du after all, but used differently. 'du -kx' without -s prints a line per directory as it finishes it, and always after everything inside it. Reading that stream gives an exact running total -- a directory's line already contains the children counted from earlier lines, so they are swapped out for it rather than added again -- which is the streaming and the floor this item wanted, at du's speed. End to end on the author's disk: 9.4s before, 5.7s now, same total to the byte.

The walker survives as --walk: no subprocesses, same numbers, about twice as slow. It is tested against du as an oracle on sparse files, hard links, symlinks, unreadable directories and a real nested mount (hdiutil-attached volume: du -skx and the walker both reported 25.0M and both excluded the 12M on the other filesystem, where plain du -sk reported 37.0M).

Verified against the two conditions this item worried about, both live on the author's machine: OrbStack was running (docker server 29.4.0 answering) and an NFS mount sits in HOME. Byte-identical to du on all eight large trees including the 28.2G OrbStack disk.

Writing the tests found a real defect: Measurer.stop() set the stop flag for the workers but run() only checked the cancel event, so stopping from outside left the driver spinning until the 180s budget expired. Fixed; test_stopping_kills_what_is_still_running covers it.
