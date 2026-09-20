---
id: 14
title: The Linux catalog is still thin
type: feature
status: backlog
milestone: v1.2
created: 2026-09-20
updated: 2026-09-20
priority: p2
effort: m
area: catalog
---

## Problem

## Proposal

## Acceptance criteria

- [ ]

## 2026-09-20

v1.1 gave Linux the XDG twins of what macOS already had. That is the layout, not the coverage. Missing, and each of them routinely large:

- system-wide Flatpak and snap: /var/lib/flatpak, /var/lib/snapd/snaps, ~/.local/share/flatpak is there but the system one is usually the big one
- ~/.ccache, the classic location, which is where ccache still puts things unless told otherwise
- Neovim and Vim: ~/.local/share/nvim, ~/.cache/nvim, ~/.vim/plugged, ~/.local/state/nvim
- Linuxbrew: /home/linuxbrew/.linuxbrew, ~/.cache/Homebrew
- distro package caches: /var/cache/apt/archives, /var/cache/pacman/pkg, /var/cache/dnf, /var/cache/zypper. Rated review, never safe, and some need root to read -- but pacman package caches reaching tens of gigabytes is ordinary and a disk tool that cannot see them is not finished
- AUR helpers: ~/.cache/yay, ~/.cache/paru
- virtualenv app data: ~/.local/share/virtualenv
- newer Python tooling: ~/.cache/pdm, ~/.cache/hatch, ~/.cache/pip already there
- ~/.cache/golangci-lint, ~/.cache/staticcheck
- rootful podman: /var/lib/containers

Acceptance criteria
- [ ] Each entry has a note, a safety rating and a command or a deliberate blank
- [ ] Nothing that needs root is rated safe
- [ ] The catalog invariant tests still pass
- [ ] README updated
