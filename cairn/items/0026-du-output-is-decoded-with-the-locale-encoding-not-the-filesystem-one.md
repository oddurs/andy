---
id: 26
title: du output is decoded with the locale encoding, not the filesystem one
type: bug
status: done
milestone: v1.3
created: 2026-09-20
updated: 2026-09-20
priority: p0
effort: s
area: scanner
---

## What happens

`DuMeasurer` reads du through `text=True`, which decodes using the locale
encoding. Paths do not come from the locale; they come from the filesystem.

In a C locale — `PYTHONCOERCECLOCALE=0`, which cairn 0012 established is a
configuration andy supports — that encoding is ASCII, and the first non-ASCII
path in du's output raises `UnicodeDecodeError` inside `_step`. Which is
caught:

```python
except Exception:
    pass
```

So the walk stops where the undecodable path was and reports whatever it had
counted so far, as though it were the whole answer. Silent under-reporting,
which is the worst of the three possible failures: the traceback would have
been better, and 0020's over-count at least looked wrong.

## Why it is not the same bug as 0020

0020 was the format: `size<TAB>path` cannot represent a path containing those
delimiters. This is the encoding: the bytes are fine and unambiguous, and andy
decodes them with the wrong codec. Same line of code, different cause, and the
0020 fallback does not trigger because the exception happens before any path is
compared.

## Reproduction

On macOS, where the filesystem encoding stays UTF-8 whatever the locale says:

```sh
PYTHONCOERCECLOCALE=0 PYTHONUTF8=0 LC_ALL=C python3 -m unittest discover -s tests
```

with a directory named `проект-日本` under the tree being measured.

## Proposal

Read the pipe as bytes and turn the path into text with `os.fsdecode`, which
uses the filesystem encoding and `surrogateescape` — so a path that is not
valid in any encoding still round-trips back to the same bytes. That is the
only correct answer for a path, and it is what the `find` output already gets:
`find_artifacts` has used `os.fsdecode` since 1.0.

## Acceptance criteria

- [x] du's output is decoded as filesystem paths, not as locale text
- [x] A non-ASCII path measures correctly under `LC_ALL=C`
- [x] A path that is not valid UTF-8 at all does not stop the walk
- [x] The suite passes in a C locale on both platforms
