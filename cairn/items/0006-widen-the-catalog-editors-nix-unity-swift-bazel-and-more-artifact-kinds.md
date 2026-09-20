---
id: 6
title: 'Widen the catalog: editors, Nix, Unity, Swift, Bazel, and more artifact kinds'
type: feature
status: done
milestone: v1.1
assignee: Oddur Sigurdsson
created: 2026-09-20
updated: 2026-09-20
priority: p2
effort: m
area: catalog
---

## Problem

The catalog knows roughly 100 locations and misses several that are routinely
among the largest things on a developer's disk. On the author's machine the
biggest unclassified figure is `2.4G  other in ~/.cache` — a category whose
whole job is to hold what andy could not name.

## Proposal

Add, keeping the existing rule that a location only appears if it exists:

**Editors and IDEs** (`dev app caches`, which today holds five entries)
- JetBrains: `~/Library/Caches/JetBrains`, `~/Library/Application Support/JetBrains`
- VS Code / Cursor / Windsurf: `Code/Cache`, `CachedData`, `CachedExtensions`,
  `User/workspaceStorage`, and the extension trees under `~/.vscode*/extensions`
- Zed: `~/Library/Caches/Zed`, `~/.local/share/zed`
- Xcode's `~/Library/Developer/Xcode/iOS DeviceSupport` is already there;
  `watchOS`/`tvOS` DeviceSupport is not

**Toolchains and runtimes**
- Nix: `/nix/store` — marked `review`, never `safe`, and only when the store is
  on the same filesystem
- Unity: `~/Library/Unity/cache`, per-project `Library/`
- Swift: `~/Library/Caches/org.swift.swiftpm`, `.build` in a project
- Bazel output bases under `/private/var/tmp/_bazel_$USER`
- Deno and Bun are in; `~/.bun/install/cache` separately is not

**Project artifacts** — new entries for `ARTIFACTS_STRICT`
- `.gradle/caches` inside a project, `.idea`, `.vs`, `.cache`, `.output` (nitro),
  `.wrangler`, `.vercel`, `.netlify`, `.sst`, `storybook-static`, `.expo`,
  `.metro`, `Library` beside an `Assets` folder (Unity), `.build` (SwiftPM),
  `bazel-*` symlink targets

**Models and datasets**
- `~/.cache/huggingface` is in; `~/.cache/torch`, `~/.keras`, `~/.cache/whisper`,
  `~/Library/Application Support/llama.cpp` are not

Every addition needs the same four things the existing entries have: a category,
a one-line note saying what it actually is, a reclaim command, and an honest
safety rating. An entry without a good reclaim command is still worth listing —
`review` with an empty command is a valid row.

## Notes

Judgement, not volume. A wrong `safe` rating on something irreplaceable is the
worst bug this program could have, worse than missing a directory entirely. When
unsure, rate it `review`.

## Acceptance criteria

- [x] `other in ~/.cache` is meaningfully smaller on a developer machine
- [x] Every new entry has a note, a safety rating, and a command or a
      deliberate blank
- [x] Nothing new is rated `safe` unless it genuinely regenerates itself
- [x] `--commands` output still reads as a script a person would run
- [x] README's "What it looks at" list updated to match

## 2026-09-20

The item's list was written from the README rather than the source, and overestimated what was missing: JetBrains, VS Code, Cursor, Zed, Bazel, Nx, Playwright, Puppeteer and Electron were already in the catalog. What was actually missing came from measuring instead of guessing -- du -kxd 1 over ~/.cache, ~/Library/Caches and ~/Library/Application Support, minus everything the catalog already knew.

That found whisper (1.6G), the two pnpm side caches (764M + 517M), VS Code's ShipIt updater (901M), zig (195M) and node-gyp (128M) on this machine alone. 'other in ~/.cache' went from 2.4G to 180M, which was the criterion.

The rest is breadth for machines unlike this one: Nix, conda and anaconda environments, Julia, Unity, Unreal, Godot, PlatformIO, ESP-IDF, Emscripten, Coursier, Ivy, sbt, pipenv, rebar3, cpanm, tvOS and macOS device support, XCTest devices, Windsurf. 110 entries to 162.

Added ARTIFACT_SAFETY so a project artifact kind can be rated something other than 'rebuild', because adding .idea and vendor without it would have told people their editor state and their vendored source regenerate themselves. Both are 'review'. A catalog test now asserts that nothing in models & datasets and nothing whose path contains 'envs' is rated safe -- it immediately caught that I had filed Triton's compiled-kernel cache under models, where its correct 'safe' rating looked like a claim that weights rebuild themselves. Moved to build caches.
