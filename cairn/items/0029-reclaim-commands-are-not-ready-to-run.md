---
id: 29
title: Reclaim commands are not ready to run
type: feature
status: done
milestone: v1.4
assignee: Oddur Sigurdsson
created: 2026-09-21
updated: 2026-09-21
priority: p1
effort: m
area: output
---

## Problem

## Proposal

## Acceptance criteria

- [ ]

## 2026-09-21

From --commands today, on a machine where andy knows every path involved:

    # cargo/maven target  (24.2G, rebuild)
    # cargo clean   # run inside the project

    # node_modules  (8.6G, rebuild)
    # find <root> -name node_modules -maxdepth 4 -prune -exec rm -rf {} +

    # rustup toolchains  (6.6G, review)
    # rustup toolchain list   # then: rustup toolchain uninstall <name>

andy found thirteen cargo targets and knows where each one is. It found 229 project artifacts. It has the name of every rustup toolchain, because 0016 made itemisation work. And it prints `<root>`, `<project>` and `<name>` for the user to go and look up again.

The output is a script that cannot be run without editing, which makes the read-it-before-you-run-it rule harder to follow rather than easier: a person filling in placeholders by hand is a person making mistakes with rm -rf.

Proposal. Emit the paths andy measured. A group becomes its members, largest first, each line naming a real directory and carrying its size, so the reader can stop partway down and have reclaimed a known amount. Where a tool wants to be told rather than have its directory removed -- cargo clean, rustup toolchain uninstall -- name the real target: `cargo clean --manifest-path ~/Code/rsst/Cargo.toml`, `rustup toolchain uninstall 1.85-aarch64-apple-darwin`.

Every line stays commented. This makes the script more useful and no more dangerous; the danger was always in the rm, and a wrong hand-typed path is worse than a right generated one.

Also print what the whole script would reclaim, and per section, so the reader knows what they are buying.

Acceptance criteria
- [x] No placeholder survives where andy knows the value
- [x] A group expands to its measured members, largest first, each with its size
- [x] Paths are quoted so a space or a newline cannot split a command
- [x] Section and script totals are printed
- [x] Every line is still commented, and a test asserts it

## 2026-09-21

The biggest change is not the substitution, it is what the section now reads like. Before: one line per kind with a placeholder, so "cargo/maven target (24.2G)" and a command you had to go and resolve thirteen times. After: thirteen lines, each naming a directory and carrying its size, largest first, so a reader can stop partway down having reclaimed a known amount.

Paths are absolute and shlex-quoted rather than tilde-shortened. Tilde reads better and does not survive quoting, and a path with a space in it that splits an rm -rf into two arguments halfway through is the one mistake this program must never help anybody make. A placeholder andy cannot fill -- asdf wants a plugin name that is not in the path -- is left standing, so it still reads as something to supply.

Two things fell out of having real values. `rustup toolchain list # then: rustup toolchain uninstall <name>` existed because andy could not name the toolchain; now it can, so the list step is gone, and the same for ollama and simctl. And the notes had to be grouped: thirteen identical explanations between thirteen different paths buried the only part of the section that varied.
