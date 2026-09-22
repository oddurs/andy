---
id: 45
title: Every preference is a flag you must type every time
type: feature
status: done
milestone: v2.1
created: 2026-09-22
updated: 2026-09-22
priority: p1
effort: m
area: config
---

## Problem

## Proposal

## Acceptance criteria

- [ ]

## 2026-09-22

Every preference andy has is a flag: which directories to scan, the size floor, how many largest items, whether to use the mouse, which engine measures, and now the theme. Someone who keeps their code in ~/src types it every time, or aliases it.

Proposal. A config file at $XDG_CONFIG_HOME/andy/config, in the plain `key = value` form Ghostty uses, with `#` comments. Custom themes go in `[theme NAME]` sections below. Read with configparser, because andy supports Python 3.9 and tomllib only arrived in 3.11 -- a zero-dependency program cannot take a TOML parser as a dependency, and a hand-written one is a second program to maintain.

    theme  = terminal
    roots  = ~/src ~/work
    min    = 50M
    top    = 20
    mouse  = no

    [theme mine]
    inherit     = terminal
    interactive = magenta

Precedence is the obvious one: a flag beats the file, the file beats the default. `andy --show-config` prints every setting with where its value came from, because a config that silently does not apply is the most frustrating kind.

A config is something a person wrote, so it must never be why andy fails to start. An unknown key, a bad value or a file that will not parse warns once on stderr, names the line, and carries on with the defaults.

Acceptance criteria
- [x] The file is read from $XDG_CONFIG_HOME/andy/config, or --config PATH
- [x] Every existing preference can be set there
- [x] Flags beat the file, the file beats the defaults
- [x] --show-config says what each value is and where it came from
- [x] A broken file warns and carries on; nothing in it can stop andy starting
- [x] Runs on Python 3.9 with nothing installed

## 2026-09-22

A config you write must never be why andy fails, and working through every way to get one wrong found three gaps the first version had: a broken custom theme was only reported once you switched to it, so you found out on the day rather than when you wrote it; a file that would not parse reported configparser own "Source contains parsing errors" with no line; and an unreadable file was described as not found. All three fixed and tested.

`colour` is accepted as well as `color`, because andy says colour everywhere and a setting rejected for its spelling is a setting the user believes they set.

The first build forgot `import re` and every test passed, because nothing had yet written a config file for the code to read. The end-to-end tests now do.
