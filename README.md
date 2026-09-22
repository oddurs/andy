# andy

[![test](https://github.com/oddurs/andy/actions/workflows/test.yml/badge.svg)](https://github.com/oddurs/andy/actions/workflows/test.yml)

A read-only accounting of where developer tooling hides your disk space, on
macOS and Linux.

Container disk images, package manager caches, language toolchains, Xcode
leftovers, simulator disks, model weights and per-project build output — found,
measured and ranked, with the command that would reclaim each one.

`andy` never deletes, moves or modifies anything. It shows you the commands;
running them is your decision.

```
 andy  228G volume · 218G used · 10.0G free  █████████████████▎ 96%

  project artifacts      36.8G  ████████████████████████████ 221
  containers & vms       29.4G  ██████████████████████▍      3
  toolchains & runtimes   6.5G  ████▉                        2
  package caches          5.0G  ███▊                         9
  build & test caches     4.7G  ███▋                         4
  git repositories        331M  ▎                            34
  dev app caches         53.5M                               5
                         ─────
  total                  82.8G  38% of used space

  of which  8.2G regenerates itself   66.5G costs you a rebuild   8.1G wants a look first

 largest items

  28.2G  r  OrbStack             ~/Library/Group Containers/HUAQ24HBR6.dev.orbstack
   7.5G  r  parser/target        ~/Code/parser/target
   5.7G  !  rustup toolchains    ~/.rustup/toolchains
   4.0G  r  engine/target        ~/Code/engine/target
   3.8G  r  api/target           ~/Code/api/target
   2.4G  s  other in ~/.cache    ~/.cache
   2.4G  s  pnpm store           ~/Library/pnpm/store
   2.2G  r  Playwright browsers  ~/Library/Caches/ms-playwright

  s regenerates itself   r costs a rebuild   ! wants a look first
```

## Install

One file, Python 3.9+, no dependencies. It needs `du`, which is on every Unix,
and `curses` only for `andy -i` — every other mode runs on a Python built
without it.

```sh
curl -o /usr/local/bin/andy \
  https://raw.githubusercontent.com/oddurs/andy/main/andy
chmod +x /usr/local/bin/andy
```

Or clone and symlink it wherever you keep things:

```sh
git clone https://github.com/oddurs/andy.git
ln -s "$PWD/andy/andy" ~/.local/bin/andy
```

## Use

```sh
andy                  # the ranked summary above
andy -i               # browse it interactively
andy --delta          # what changed since the last run
andy --tree           # every location, grouped
andy --commands       # reclaim commands as a commented shell script
andy --json           # machine-readable, for scripts and dashboards
andy ~/work ~/src     # scan these project roots instead of the defaults
```

### What changed

`andy --delta` subtracts the previous scan from this one. The interesting
number on a full disk is rarely the biggest thing — it is the thing that was
not there last week.

```
 andy  change since the previous scan, 3 days ago

 changed  2 locations

   +4.2G  cargo/maven target   3.1G → 7.3G
   -840M  Xcode DerivedData    1.2G → 412M

 new  8.0M in 1 location andy had not measured before, which may mean created
      or merely recognised

   8.0M  dashboard/node_modules   ~/Code/dashboard/node_modules

  net  +3.4G  across the 2 locations andy could compare
```

Three totals rather than one, because they are not equally trustworthy. A
location with no previous figure might be newly created, or it might be one
andy only started recognising when the catalog grew — so it is counted apart
from the change andy can actually vouch for. The interval is stated rather than
implied: the comparison is against whenever andy last ran, which might be ten
minutes or three weeks.

Useful flags: `-n N` how many largest items to list, `-m SIZE` hide anything
smaller (default `10M`), `--no-projects` to skip the per-project scan when you
just want the caches, `--fresh` to ignore cached sizes, `--no-mouse` to leave
your terminal's own text selection alone.

### The interactive browser

`andy -i` opens a tree you can walk. Sizes stream in as they are counted — each
one climbing as `du` reports the directories underneath it — so it is usable
well before the scan finishes.

```
 ▾ PROJECT ARTIFACTS                             37.5G █████████▍
   ▾ cargo/maven target                     r    24.2G ████████████▉
       rsst/target                 ~/Code   r     7.5G ████
       poptop/target               ~/Code   r     4.3G ██▎
   ▾ node_modules                            r    8.6G ████▌
       traintime/node_modules      ~/Code   r     637M ▎
```

**A bar is the share of the thing it sits inside** — a category against
everything mapped, and everything below it against that category. So two rows
of the same size draw the same bar wherever they are, and the 637M above reads
as the rounding error it is.

It used to be drawn against the largest item at each level, which kept every
tier busy and made that 637M `node_modules` and the 7.5G `target` four lines
above it both draw full. The bar is the loudest thing on the row; it should be
the one you can trust.

**The middle column carries what the label does not.** A project artifact is
labelled by its path relative to the scan root, so all that is left to say is
which root — worth a column when you scan several, and a narrow repeated word
when you do not.

**The mark is the safety rating**, the same `s` / `r` / `!` the summary prints:
the list you decide from is the one that needs it.

### The design language

A terminal offers six channels, and each one here has exactly one job — because
a channel with two jobs has none. If you have to know which column you are
looking at before a colour means anything, you are reading the column.

| channel | job |
| --- | --- |
| position | what kind of thing this is — the grid |
| length | proportion. The bar, and nothing else |
| weight | structure. **bold** heads, dim supports, normal is content |
| hue | consequence (green, yellow, red) or interaction (cyan). Never data |
| reverse | the cursor. Only ever the cursor |
| glyph | state: open, closed, marked, unmeasured, a floor |

Magnitude is deliberately absent from that list. The figure states it and the
bar shows it; colouring it as well said one fact three times, and it was
spending the channel that consequence needed — so a row used to print a red
size beside a green mark, *enormous* and *harmless*, two columns apart.

Two forms carry every label and value in the program: a **field** is a fact,
with a dim key right-aligned in a fixed gutter, and a **hint** is something you
can press, with a cyan key and a dim label. There is no third. One skeleton
carries every list row — *state, name, context, consequence, quantity,
proportion* — which is why the detail pane reads as the row you pointed at
rather than as a different kind of thing.

None of it depends on colour. A monochrome terminal loses emphasis and no
information: every rating is a character before it is a hue.

### The area map

Press `m` for a treemap: every category becomes a rectangle whose **area** is its
share of the total. Click a rectangle to open it, right-click or `←` to come back
up. The real thing fills each cell with a grey tone; here they are outlined.

```
 all categories                                                        83.4G in 7
 +2 too small to draw · 389M

 ┌─ project artifacts ──────────────┐ ┌─ containers & vms ────────┐ ┌─ t…┐ ┌─ pac… ┐
 │ 36.5G                   44%      │ │ 29.4G            35%      │ │    │ │ 5.0G  │
 │                                  │ │                           │ │    │ │       │
 │                                  │ │                           │ │    │ │       │
 │                                  │ │                           │ │    │ └───────┘
 │                                  │ │                           │ │    │
 │                                  │ │                           │ │    │ ┌─ bui… ┐
 │                                  │ │                           │ │    │ │ 4.7G  │
 │                                  │ │                           │ │    │ │       │
 │                                  │ │                           │ │    │ │       │
 └──────────────────────────────────┘ └───────────────────────────┘ └────┘ └───────┘
```

Area carries the magnitude, so colour is left to do one job - separate
neighbouring cells - which a single grey ramp does identically on a light or a
dark terminal, since each cell supplies its own background. Every cell is
labelled, so nothing depends on telling two shades apart.

### The mouse

The interactive view is fully mouse-driven: click a row to select it, click the
`▸` to open a branch, double-click a folder row to reveal it in Finder, and
right-click to copy a reclaim command. The wheel scrolls, the left edge is a
scroll bar you can click, and every hint along the bottom is a button. In the
map, click to select and double-click to drill in.

Mouse reporting takes over your terminal's own click-and-drag text selection -
hold **shift** to get it back for a moment, or run `andy -i --no-mouse` to leave
the mouse alone entirely.

| key | |
| --- | --- |
| `j` `k` `↑` `↓` | move; `ctrl-d`/`ctrl-u` half page, `g`/`G` ends |
| `↵` `space` `tab` | expand or collapse; `e`/`E` expand or collapse all |
| `/` | filter by name or path; `esc` clears |
| `s` | sort by size or name |
| `a` | also show items under 10M |
| `space` | mark this row; `C` copies every marked row as one script |
| `c` | copy the reclaim command to the clipboard |
| `y` | copy the path; `o` reveals it in Finder |
| `m` | the area map; `↵` opens a cell, `←` backs out |
| `d` | toggle the detail pane; `r` rescan; `?` keys; `q` quit |

## What it looks at

Around 170 known locations per platform, 214 across both, and only those that
exist on your machine:

- **Containers and VMs** — OrbStack, Docker Desktop, Colima, Lima, Podman,
  Rancher Desktop, minikube, Vagrant, UTM, VirtualBox, Parallels. When a Docker
  daemon is reachable it also shows the live image / volume / build-cache split.
- **Package caches** — npm, npx, pnpm, Yarn, Bun, Deno, Cargo, Go modules, pip,
  uv, Poetry, pipenv, Maven, Gradle, Ivy, sbt, Coursier, CocoaPods, Carthage,
  SwiftPM, Homebrew, RubyGems, cpanm, Composer, NuGet, pub, Stack, Cabal, opam,
  Hex, rebar3, Conan, vcpkg, conda, Julia.
- **Toolchains and runtimes** — rustup, nvm, fnm, nodenv, Volta, pyenv, rbenv,
  jenv, tfenv, asdf, mise, SDKMAN, local JDKs, Go SDKs, ghcup, .NET, Bun,
  Android SDK and emulators, Flutter, Nix, PlatformIO, ESP-IDF, Emscripten,
  Unity, Unreal, Godot.
- **Xcode and simulators** — DerivedData, simulator devices (named from their
  `device.plist`, not just UDIDs), simulator runtimes, volumes and caches,
  iOS/watchOS/tvOS/macOS device support, XCTest devices, archives, previews,
  Xcode's own cache.
- **Linux system storage** — `/var/lib/flatpak`, snap revisions, rootful
  podman, Linuxbrew, and the distro package caches: apt, pacman, dnf, zypper,
  yay, paru. Some need root to read, and are rated accordingly.
- **Editors on Linux too** — Neovim data, state and cache, vim-plug plugins,
  and the XDG homes of everything above.
- **Build and test caches** — Go build cache, Turborepo, Nx, Bazel, ccache,
  sccache, Zig, Triton, node-gyp, electron-gyp, TypeScript, Selenium,
  Playwright, Puppeteer, Cypress, Electron, pre-commit, Terraform.
- **Models and datasets** — Ollama, Hugging Face, PyTorch hub, Whisper, Keras,
  LM Studio, GPT4All, llama.cpp, Kaggle.
- **Editors** — VS Code, Cursor, Windsurf and Zed caches, cached data, extension
  archives and workspace state; JetBrains and Android Studio indexes.
- **Project artifacts** — `node_modules`, `target`, `.venv`, `.next`, `Pods`,
  `.gradle`, `.terraform`, `.wrangler`, `.expo`, `storybook-static`,
  `cmake-build-*`, `.idea` and about forty others, found under `~/Code`,
  `~/Projects`, `~/dev` and the other usual roots, grouped by kind.
- **Git repositories** — object databases, largest first.

A name alone is never enough to call something disposable. `target` and `build`
only count as build output when a manifest sits beside them; a `.cache` in a
project with no `package.json` is somebody's data, not a cache.

Every item carries a safety rating: **safe** regenerates itself, **rebuild** is
fine to remove but costs you a rebuild, **review** may hold something you want.
Editor state, vendored dependencies and anything holding model weights are
never rated safe, whatever their name suggests. The summary totals the three, so
the first thing you see is how much of the pile you can actually act on.

### Commands you can read and then run

`andy --commands` writes the reclaim commands as a commented shell script, with
the paths filled in — it found the directories, so it names them rather than
leaving you a `<project>` to look up and retype.

```sh
# ---- toolchains & runtimes  7.3G -----------------------------------

#   A full Rust toolchain per channel. Old nightlies add up fast.

# stable-aarch64-apple-darwin  (2.1G, review)
# rustup toolchain uninstall stable-aarch64-apple-darwin

# 1.98.1-aarch64-apple-darwin  (1.3G, review)
# rustup toolchain uninstall 1.98.1-aarch64-apple-darwin
```

Largest first, so you can stop partway down having reclaimed a known amount.
Paths are absolute and shell-quoted, because a path with a space in it that
splits an `rm -rf` into two arguments is the one mistake this program must never
help you make. Every line is still commented; nothing here has been run.

## Notes

**Sizes don't double count.** When one measured location sits inside another,
the inner one is subtracted from the outer — so `~/.cache/uv` is listed on its
own and `other in ~/.cache` holds only the remainder. Docker's live breakdown is
shown but marked as a view onto the VM disk it lives in, never added to the
total, because those are the same bytes.

**The first run is slow, but nothing waits for the end.** It is `du` walking real
trees with a cold filesystem cache; expect a minute or two if you have a large
container disk. andy runs one `du` per location and reads its output as it
arrives rather than waiting for a total, so every figure climbs while the scan
is still going and the tree is worth looking at from the first second. Results
are cached in `~/.cache/andy/scan.json`, so later runs start from the previous
numbers and refresh in seconds. `--fresh` skips the cache.

**Nothing is allowed to hang.** `du` on the data directory of a *running*
container VM can block on I/O for many minutes at no CPU at all, and a network
mount can do the same. The measurement phase is bounded, and because the totals
are already climbing, running out of time costs precision rather than the
answer: what had been counted is shown as a floor — `≥ 20.1G` — and marked
incomplete, instead of being discarded. Any `du` still running when andy stops
is killed rather than orphaned onto that disk. `du -x` keeps every walk on one
filesystem, so a mounted share is never counted as local disk.

**`--walk` measures without `du`.** The same numbers from a different route:
andy walks the trees itself, counting `st_blocks` exactly as `du -k` does, with
the same rules about filesystem boundaries, symlinks and hard links. It is about
twice as slow — the per-file work `du` does in C is work Python threads have to
take turns at — so it is not the default, but it is there for a machine where
spawning a few hundred short-lived processes is unwelcome, or where `du` behaves
unlike the two implementations this was tested against.

**`~/Code` and `~/code` are one directory** on a case-insensitive volume. Roots
are de-duplicated by inode, not by spelling, so nothing is counted twice.

**Linux keeps the same things somewhere else.** The catalog is split: the
portable half — `~/.cache`, `~/.cargo`, `~/.rustup`, `~/.npm`, `~/go`, `/nix`
and the rest — is shared, and each platform adds its own. `~/Library/...` and
everything Xcode is tagged macOS-only; `~/.config`, `~/.local/share` and the XDG
caches are tagged Linux. Clipboard is `pbcopy`, or `wl-copy` / `xclip` / `xsel`,
whichever answers first; `o` opens the containing directory through `xdg-open`.

**`XDG_CACHE_HOME` and friends are honoured**, on both platforms, so andy looks
where your tools actually put things rather than where the platform suggests.
`XDG_CONFIG_HOME`, `XDG_DATA_HOME` and `XDG_STATE_HOME` too. A relative value is
ignored, as the spec requires.

**It degrades instead of failing.** In a terminal that cannot encode box
drawing — a C locale with PEP 538 coercion turned off, or an 8-bit encoding —
andy draws the same report in ASCII rather than dying on a `UnicodeEncodeError`.
A `HOME` that was never created, which is ordinary in a container or a systemd
unit, costs you the volume line and nothing else.

Docker differs in kind rather than in path. On macOS the daemon lives in a VM
whose disk andy measures directly, so `docker system df` describes the same
bytes and is shown but never added. On Linux there is no VM: `/var/lib/docker`
is the real thing, reading it needs root, and the daemon's own report is the
only figure available without privileges — so on Linux it counts toward the
total, and `/var/lib/docker` is deliberately absent from the catalog.

**Totals are smaller than "used".** andy maps developer storage, not your
whole disk — photos, mail, iOS backups and system data are deliberately out of
scope.

## Development

The roadmap and the open issues live in the repository, as Markdown under
`cairn/items`, rendered to `ROADMAP.md`.

```sh
python3 -m unittest discover -s tests     # the whole suite
python3 -m unittest discover -s tests -v  # one line per test
```

Around 300 tests, including the interactive browser: most of it is arithmetic
over a model and runs against a screen object that records instead of
rendering, and the rest is driven through a pty.

The tests need nothing installed. andy is a zero-dependency program, and a test
suite you have to `pip install` something to run is a test suite that stops
telling you whether that is still true — so it is stdlib `unittest`, and
`tests/andymod.py` does the one awkward thing, importing an executable that has
no `.py` on the end of it.

## License

MIT
