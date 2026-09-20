---
id: 25
title: The browser hides the locations it could not measure
type: bug
status: done
milestone: v1.3
created: 2026-09-20
updated: 2026-09-20
priority: p1
effort: s
area: tui
---

## What happens

`build_rows` drops any row with nothing in it:

```python
def visible(node):
    ...
    if node.size <= 0 and not node.children:
        return False
```

A location whose walk never finished has `measured is None`, so `size` is 0 and
no children, so it never appears. The interactive browser silently omits
exactly the locations it could not measure — a running container VM, a network
mount, a directory it could not read. Those are the ones most worth saying
something about, and `--tree` and the default report both do.

## The tell

`draw_body` already handles the case:

```python
if node.blocked and node.measured is None:
    return "     ?"
```

That branch cannot be reached, because `build_rows` filtered the row out before
`draw_body` ever sees it. Someone wrote the rendering for a row the list could
never contain.

## Found by

A cairn 0023 test that put a blocked node in the model and asked the browser to
show it selected.

## Proposal

Keep a blocked row: `if node.size <= 0 and not node.children and not
node.blocked`. The `?` becomes reachable, and the detail pane already explains
what happened — "incomplete — the walk ran out of time here".

## Acceptance criteria

- [x] A location that could not be measured appears in the browser
- [x] It reads as `?` rather than as zero, which would be a different claim
- [x] Selecting it explains why in the detail pane
- [x] It is still hidden by a filter that does not match it
