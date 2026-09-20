---
id: 24
title: A narrow terminal crashes the footer
type: bug
status: done
milestone: v1.3
created: 2026-09-20
updated: 2026-09-20
priority: p0
effort: s
area: tui
---

## What happens

`draw_footer` drops key hints until the remaining ones fit the width:

```python
while items:
    widths = [len(k) + 1 + len(lbl) for k, lbl, _ in items]
    if 1 + sum(widths) + 3 * (len(items) - 1) <= w - 2:
        break
    items.pop(0) if len(items) > 6 else items.pop(4)
```

Once six or fewer remain it pops index 4, and at four or fewer that index does
not exist:

```
  File "andy", line 3009, in draw_footer
    items.pop(0) if len(items) > 6 else items.pop(4)
IndexError: pop index out of range
```

`draw()` is called from the main loop, so this takes the browser down. `put()`
swallows `curses.error` but this is an `IndexError` and nothing catches it.

## When

Any terminal too narrow for four hints — about 30 columns. A split pane, a
phone-sized SSH window, or a tmux pane beside an editor.

## Found by

The first headless drawing test written for cairn 0023, sweeping sizes from
6x30 upward. Eleven hundred lines of browser had never been drawn at a width
nobody happened to try.

## Proposal

Clamp the index: `items.pop(0 if len(items) > 6 else min(4, len(items) - 1))`.
The loop already terminates correctly on an empty list, so a width that fits
nothing draws nothing rather than raising.

## Acceptance criteria

- [x] The footer draws at every width from 1 column upward
- [x] A width that fits nothing draws an empty footer, not an exception
- [x] A size sweep covers it, so no drawing code is only ever seen at one size
