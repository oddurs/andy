---
id: 10
title: XDG base directories are ignored
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

## What should happen

## Reproduction

1.

## 2026-09-20

The Linux half of the catalog hardcodes ~/.cache, ~/.config and ~/.local/share. Those three paths are exactly the ones XDG_CACHE_HOME, XDG_CONFIG_HOME and XDG_DATA_HOME exist to move, and the developers most likely to set them are the ones with the fullest disks.

Reproduced: with XDG_CACHE_HOME=/tmp/h/xdgcache holding a 20M go-build cache and XDG_CONFIG_HOME holding 20M of VS Code cache, andy reports neither. It looks in ~/.cache and ~/.config, which are empty, and says so.

andy already reads XDG_CACHE_HOME for its own scan cache, so the file is inconsistent with itself.

Proposal: resolve the three prefixes in S(), where paths are already expanded, so the catalog keeps its readable ~/.cache/... literals and the translation happens once. Apply on both platforms -- a tool that honours XDG_CACHE_HOME on Linux honours it on macOS too, and andy should look where the tool actually put things. XDG_STATE_HOME as well, for completeness. A relative value is ignored, as the spec requires.

Acceptance criteria
- [x] XDG_CACHE_HOME, XDG_CONFIG_HOME, XDG_DATA_HOME and XDG_STATE_HOME are all honoured
- [x] Unset behaviour is unchanged: ~/.cache, ~/.config, ~/.local/share, ~/.local/state
- [x] A relative or empty value falls back to the default rather than producing a relative path
- [x] expand= globs resolve through the same translation
- [x] Tested by setting the variables and finding the files
