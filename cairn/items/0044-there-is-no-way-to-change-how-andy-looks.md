---
id: 44
title: There is no way to change how andy looks
type: feature
status: done
milestone: v2.1
assignee: Oddur Sigurdsson
created: 2026-09-22
updated: 2026-09-22
priority: p1
effort: m
area: tui
---

## Problem

## Proposal

## Acceptance criteria

- [ ]

## 2026-09-22

v2.0 made every attribute a role: heading, content, supporting, interactive, selected, and consequence for each of safe, rebuild and review. So a theme is a table from those names to a style, and nothing else in the program has to change to support one.

Proposal. A style is a short phrase: an optional colour and any attributes.

    interactive = cyan
    supporting  = dim
    review      = bright-red bold
    heading     = default bold
    safe        = color108          # an xterm-256 index, for those who want one

Colours are the sixteen ANSI names (black red green yellow blue magenta cyan
white, and bright- of each), `default` for the terminal foreground, or colorN.
Ship three:

  terminal   the default. ANSI and attributes only, map outlined -- inherits
  mono       no colour at all, emphasis by attribute alone. NO_COLOR chosen on purpose
  classic    the 1.x look, grey-shaded map included

A custom theme names the one it starts from and overrides roles, so a person
who only wants a different cyan writes one line.

One theme drives both halves. The plain-text reports have their own tiny ANSI
writer, and a theme that recoloured the browser but not `andy --commands` would
be exactly the disagreement v2.0 removed.

Keep the language honest: themes restyle roles, they do not add them. A theme
cannot make magnitude coloured because there is no magnitude role to colour.

Acceptance criteria
- [x] Three built-in themes, the default inheriting from the terminal
- [x] A custom theme can start from another and override single roles
- [x] The same theme styles the browser and the plain-text reports
- [x] A bad colour or attribute warns and falls back, never crashes
- [x] Themes can only restyle the roles the design language defines
