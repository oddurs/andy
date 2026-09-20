# andy

A read-only accounting of where developer tooling hides your disk space, on macOS.

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

One file, Python 3.9+, no dependencies. `curses` and `du` ship with macOS.

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
just want the caches, `--fresh` to ignore cached sizes.

### The interactive browser

`andy -i` opens a tree you can walk. Sizes stream in as they are measured,
so it is usable before the scan finishes.

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

| key | |
| --- | --- |
| `j` `k` `↑` `↓` | move; `ctrl-d`/`ctrl-u` half page, `g`/`G` ends |
| `↵` `space` `tab` | expand or collapse; `e`/`E` expand or collapse all |
| `/` | filter by name or path; `esc` clears |
| `s` | sort by size or name |
| `a` | also show items under 10M |
| `c` | copy the reclaim command to the clipboard |
| `y` | copy the path; `o` reveals it in Finder |
| `d` | toggle the detail pane; `r` rescan; `?` keys; `q` quit |

## What it looks at

Roughly 100 known locations, and only those that exist on your machine:

- **Containers and VMs** — OrbStack, Docker Desktop, Colima, Lima, Podman,
  Rancher Desktop, minikube, Vagrant, UTM, VirtualBox, Parallels. When a Docker
  daemon is reachable it also shows the live image / volume / build-cache split.
- **Package caches** — npm, npx, pnpm, Yarn, Bun, Deno, Cargo, Go modules, pip,
  uv, Poetry, Maven, Gradle, CocoaPods, Carthage, SwiftPM, Homebrew, RubyGems,
  Composer, NuGet, pub, Stack, Cabal, opam, Hex, Conan, vcpkg, conda.
- **Toolchains and runtimes** — rustup, nvm, fnm, Volta, pyenv, rbenv, asdf,
  mise, SDKMAN, local JDKs, ghcup, .NET, Android SDK and emulators, Flutter.
- **Xcode and simulators** — DerivedData, simulator devices (named, not just
  UDIDs), simulator runtimes and caches, device support, archives, previews.
- **Build and test caches** — Go build cache, Turborepo, Nx, Bazel, ccache,
  sccache, Playwright, Puppeteer, Cypress, Electron, pre-commit, Terraform.
- **Models and datasets** — Ollama, Hugging Face, PyTorch hub, LM Studio.
- **Project artifacts** — `node_modules`, `target`, `.venv`, `.next`, `Pods`,
  `.gradle`, `.terraform` and similar, found under `~/Code`, `~/Projects`,
  `~/dev` and the other usual roots, grouped by kind.
- **Git repositories** — object databases, largest first.

Every item carries a safety rating: **safe** regenerates itself, **rebuild** is
fine to remove but costs you a rebuild, **review** may hold something you want.

## Notes

**Sizes don't double count.** When one measured location sits inside another,
the inner one is subtracted from the outer — so `~/.cache/uv` is listed on its
own and `other in ~/.cache` holds only the remainder. Docker's live breakdown is
shown but marked as a view onto the VM disk it lives in, never added to the
total, because those are the same bytes.

**The first run is slow.** It is `du` walking real trees with a cold filesystem
cache; expect a minute or two if you have a large container disk. Results are
cached in `~/.cache/andy/scan.json`, so later runs start from the previous
numbers and refresh in seconds. `--fresh` skips the cache.

**`~/Code` and `~/code` are one directory** on a case-insensitive volume. Roots
are de-duplicated by inode, not by spelling, so nothing is counted twice.

**Totals are smaller than "used".** andy maps developer storage, not your
whole disk — photos, mail, iOS backups and system data are deliberately out of
scope.

## License

MIT
