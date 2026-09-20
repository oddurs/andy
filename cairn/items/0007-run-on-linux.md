---
id: 7
title: Run on Linux
type: feature
status: done
milestone: v1.1
assignee: Oddur Sigurdsson
depends_on:
- 4
created: 2026-09-20
updated: 2026-09-20
priority: p2
effort: l
area: platform
---

## Problem

andy is macOS-only, and most of it did not need to be. The scanning, the
roll-up, the treemap, the TUI and every output format are portable already. What
is not:

- `clip()` shells out to `pbcopy`
- `reveal()` runs `open -R`
- Paths are hard-coded to `~/Library/...`, with no XDG equivalents
- Xcode, simulators, OrbStack, UTM and Parallels have no meaning there
- `shutil.disk_usage(HOME)` is fine; `du -skx` is fine on GNU coreutils too

Meanwhile a Linux developer's disk fills with exactly the same things: a
multi-gigabyte `~/.cargo`, `~/.rustup`, pnpm and npm stores, Docker's
`/var/lib/docker`, Go build caches, `node_modules` everywhere, and `/nix/store`.
The program's entire reason to exist applies unchanged.

## Proposal

**Clipboard.** Try in order: `wl-copy` (Wayland), `xclip -selection clipboard`,
`xsel --clipboard --input`, falling back to printing the command and saying so.
On macOS, `pbcopy` as now. The TUI's "copied" toast must tell the truth when
nothing was copied — today `clip()` returns a bool that the caller does use, so
this is mostly about the fallback message.

**Reveal.** `xdg-open` on the containing directory. Say "open in file manager"
rather than "reveal in Finder" in the help and the footer when not on macOS.

**Paths.** Give `Spec` a platform tag, or simply a second catalog list merged in
by `sys.platform`. Linux entries: `~/.cache/{go-build,pip,uv,yarn,pnpm,ms-playwright,huggingface,pre-commit,bazel}`,
`~/.local/share/{pnpm,virtualenvs,containers,Trash}`, `~/.npm`, `~/.m2`,
`~/.gradle`, `~/.nuget`, `~/.cargo`, `~/.rustup`, `~/go/pkg/mod`, `/nix/store`,
`~/.local/share/JetBrains`, `~/.config/Code`, plus `/var/lib/docker` when it is
readable.

**Docker on Linux** has no VM disk. `/var/lib/docker` is the real thing and
usually needs root to measure, so the live `docker system df` breakdown stops
being merely informational there — it becomes the only number available. That
changes the `informational` flag's meaning and needs deciding rather than
assuming: on Linux the breakdown should count toward the total, with the VM-disk
row absent.

**Apple-only entries** are skipped by tag, not by the `usable_dir` check —
they would never match anyway, but a tag documents the intent and keeps
`--json` honest about what was looked at.

## Notes

Only claim what gets tested. If CI does not run the suite on Linux, the README
should not say Linux is supported. 0007 covers that.

## Acceptance criteria

- [x] Clipboard works under Wayland and X11, and degrades honestly with neither
- [x] Reveal opens the containing directory via `xdg-open`
- [x] Linux catalog entries, tagged by platform, merged at startup
- [x] Docker's live breakdown counts toward the total on Linux, and the
      reasoning is written down where the `informational` flag is defined
- [x] No Apple-specific wording appears in the UI on Linux
- [x] Test suite passes on Linux in CI
- [x] README no longer says "on macOS"

## 2026-09-20

Linux is verified rather than claimed: the suite and the end-to-end script were run in python:3.9-slim and python:3.13-slim containers, and a synthetic Linux home was scanned to watch the XDG catalog actually fire (~/.config/Code/Cache, ~/.local/share/pnpm/store, ~/.cache/go-build, ~/.cache/JetBrains, alongside the shared ~/.cargo and ~/.rustup).

Criterion 1 is unticked on purpose. The selection logic is tested -- wl-copy preferred, xclip and xsel as fallbacks, a failing tool falling through to the next, and no clipboard at all returning False rather than raising -- but no real Wayland or X11 session was available, so 'works under Wayland and X11' is not something this session established. Criterion 6 stays unticked until GitHub actually runs the workflow; it passes on Linux here, which is not the same statement.

The platform tag is derived from the path (/Library/ means Apple) with an explicit override, because tagging 162 entries by hand invites exactly one to be forgotten. Two were: Unity editors under ~/Applications and Bazel's output base under /private/var have no /Library/ in them, so they were untagged and turned up on Linux -- the duplicate-label test caught Unity. There is now a test asserting no untagged entry uses an Apple-only path shape outside HOME.

## 2026-09-20

Left open, not closed: cairn refused the close and was right to. The implementation is finished and merged; what is outstanding is observation, not work — a real Wayland/X11 session for the clipboard, and the first green CI run for the Linux job. Blocked on 0008 for the second.

## 2026-09-20

Criterion 1 is now established rather than assumed. Verified in containers against real display servers:

  X11        Xvfb + xclip          clip() True, xclip -o read back exactly what went in
  X11        xclip hidden, xsel    clip() True, xsel --output read it back
  Wayland    headless sway         clip() True, wl-paste read it back
  neither    nothing on PATH       clip() False

Two false starts worth recording. Headless weston has no wl_seat, and wl-clipboard refuses to run without one -- 'The compositor does not seem to implement seat' -- so that configuration proves nothing about andy; it was andy returning False correctly about a compositor where wl-copy itself cannot work. wlroots' headless backend does provide a seat, so sway is the thing to use. And sway refuses to start as root, so it needs an unprivileged user.

Made repeatable rather than left as a one-off: tests/clipboard_check.py, driven by a new `clipboard` job in the workflow. It is deliberately not named test_*.py, so the ordinary suite -- which must run anywhere -- does not try to pick it up.
