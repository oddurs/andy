---
id: 43
title: The default look does not inherit from the terminal it runs in
type: bug
status: done
milestone: v2.1
created: 2026-09-22
updated: 2026-09-22
priority: p0
effort: m
area: tui
---

## What happens

## What should happen

## Reproduction

1.

## 2026-09-22

What inheriting means, concretely, so it can be tested rather than eyeballed:

  - every foreground is the terminal default or one of the sixteen ANSI colours,
    which are exactly the ones a Ghostty, herdr, iTerm or kitty theme redefines
  - no background is ever painted except the terminal default
  - emphasis comes from attributes -- bold, dim, reverse -- which the terminal
    renders in its own palette

andy already does all three everywhere but one place. The area map fills each
cell from MAP_RAMP, six xterm-256 greys from 239 to 249 with a hard white or
black label. Those are absolute colours: on a light theme, on Catppuccin or
Gruvbox or Solarized, the map is a block of neutral grey that belongs to some
other program.

Proposal. The default theme -- called `terminal`, because that is what it
defers to -- draws the map with outlines in the dim foreground, which v2.0
already built as the colourless fallback. Cells stay separated, every cell is
still labelled, and nothing on screen is a colour the user did not pick. The
grey ramp survives, as an opt-in theme for people who liked it.

Acceptance criteria
- [x] The default theme uses only the terminal default and ANSI 0-15
- [x] It paints no background anywhere
- [x] The map draws without a fixed palette
- [x] A test enforces all three, so a future colour cannot quietly hardcode itself

## 2026-09-22

Inheriting is now a tested property rather than an intention. Three checks against the default theme on a simulated 256-colour terminal: every colour pair asks for the terminal default or ANSI 0-15, every background is -1, and the map asks for no fixed palette. Checked that they can fail by giving the theme an absolute colour in memory -- both named it ("pair 4 asks for colour 33, which no terminal theme defines") -- without touching the file.

The map was the only real offender, and the fix turned out to be better than the thing it replaced. The v2.0 colourless fallback drew two horizontal rules per cell, which the label overwrote and which let neighbours run together; it is now a proper box with the label set into the top edge -- the drawing the README had been showing all along as an illustration of the shaded version.
