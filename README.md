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

 largest items

  28.2G  OrbStack             ~/Library/Group Containers/HUAQ24HBR6.dev.orbstack
   7.5G  parser/target        ~/Code/parser/target
   5.7G  rustup toolchains    ~/.rustup/toolchains
   4.0G  engine/target        ~/Code/engine/target
   3.8G  api/target           ~/Code/api/target
   2.4G  other in ~/.cache    ~/.cache
   2.4G  pnpm store           ~/Library/pnpm/store
   2.2G  Playwright browsers  ~/Library/Caches/ms-playwright
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
andy --tree           # every location, grouped
andy --commands       # reclaim commands as a commented shell script
andy --json           # machine-readable, for scripts and dashboards
andy ~/work ~/src     # scan these project roots instead of the defaults
```

Useful flags: `-n N` how many largest items to list, `-m SIZE` hide anything
smaller (default `10M`), `--no-projects` to skip the per-project scan when you
just want the caches, `--fresh` to ignore cached sizes, `--no-mouse` to leave
your terminal's own text selection alone.

### The interactive browser

`andy -i` opens a tree you can walk. Sizes stream in as they are counted — each
one climbing as `du` reports the directories underneath it — so it is usable
well before the scan finishes.

```
 ▾ PROJECT ARTIFACTS                                                        36.9G  ████████████████████
   ▾ cargo/maven target                                                     25.3G  ████████████████████
     parser/target                                ~/Code/parser/target       7.5G  ████████████████████
     engine/target                                ~/Code/engine/target       4.0G  ██████████▋
     api/target                                   ~/Code/api/target          3.8G  ██████████▏
   ▾ node_modules                                                            7.7G  ██████▏
     dashboard/node_modules                       ~/Code/…rd/node_modules    637M  ████████████████████
```

Each bar is drawn against the largest item at that level, so every tier of the
tree stays readable.

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
never rated safe, whatever their name suggests.

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

The tests need nothing installed. andy is a zero-dependency program, and a test
suite you have to `pip install` something to run is a test suite that stops
telling you whether that is still true — so it is stdlib `unittest`, and
`tests/andymod.py` does the one awkward thing, importing an executable that has
no `.py` on the end of it.

## License

MIT
