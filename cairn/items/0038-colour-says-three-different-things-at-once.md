---
id: 38
title: Colour says three different things at once
type: bug
status: done
milestone: v2.0
created: 2026-09-21
updated: 2026-09-21
priority: p0
effort: m
area: tui
---

## What happens

## What should happen

## Reproduction

1.

## 2026-09-21

Red, yellow and green are used for four unrelated ideas:

  magnitude()    red >=10G, yellow >=1G, dim <100M     how big it is
  safety_attr()  green safe, yellow rebuild, red review  what it costs to remove
  free space     red when low, green otherwise           whether you are in trouble
  blocked        yellow                                  andy could not measure it

So one row can print a red size beside a green mark: "this is enormous" and
"this is harmless" in the same hue family, two columns apart. The reader has to
know which column they are looking at before the colour means anything, which
is the definition of a colour that means nothing.

Cyan is worse. It is the scrollbar, the disk bar, category bars, the reclaim
command, the toast message, the filter tag and the footer keys -- chrome, data,
a command, a message and a control, all the same colour.

Proposal. The warm scale means consequence and nothing else: green regenerates,
yellow costs a rebuild, red wants a look. A low free-space figure stays red
because that is consequence too -- it is the program saying this is the problem
-- and blocked stops being yellow and becomes a glyph, which is what it always
was: a state, not a severity.

Magnitude loses its colour entirely. The number says how big it is and the bar
shows it; colouring it as well is the same fact three times, and it was
spending the one channel that could have carried something else.

Acceptance criteria
- [x] Green, yellow and red appear only for consequence
- [x] Magnitude is never coloured
- [x] Cyan means one thing
- [x] A monochrome terminal loses no information, only emphasis

## 2026-09-21

Audit found the warm scale meaning four things and cyan meaning five. After: green, yellow and red mean consequence in the browser and in every report, and cyan means interaction.

The plain-text half needed the same treatment and got it. The delta report was colouring growth red and shrinkage green -- a fourth meaning, and a misleading one, since it said a 4G jump in something you can delete freely was as alarming as one in something you cannot. The sign now carries direction and the colour carries what it carries everywhere else: what removing the thing would cost. "Plenty of free space" stopped borrowing the ratings green; it is plain, and only a nearly full disk is red, because only that is the problem.
