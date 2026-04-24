# AGENTS.md — Fancode / Dreamlucid CasparCG Server fork

This repo is **dreamlucid/server** on GitHub: a **CasparCG Server** fork used for live stream playout (SRT pipelines, HTML/CEF graphics, AMCP control). Agents should treat this file plus **[BUILDING.md](BUILDING.md)** and **[README.md](README.md)** as the operational contract for **this fork**; upstream CasparCG wiki remains useful for protocol semantics.

---

## Fork identity and branching

| Item | Value |
|------|--------|
| **Remote** | `git@github.com:dreamlucid/server.git` (`origin`) |
| **Primary integration branch** | **`fc-master`** — day-to-day feature and fix work should branch from and merge back here unless instructed otherwise. |
| **Other local branches** | `master` (upstream-style), feature branches (e.g. `feat-*`) as needed. |

**CI note:** [.github/workflows/](.github/workflows/) currently run on **pull requests targeting `master` only**. Pushing to `fc-master` alone does not trigger that matrix. For work that lives on `fc-master`, either open a PR into `master` when you need the GitHub Actions gate, or ask maintainers to add `fc-master` to `pull_request.branches` in the workflow files—do not silently change CI without team agreement.

---

## Goals for agentic work (Fancode)

- **Small, reviewable PRs** with a short problem statement, approach, and **verification** (build + fork smoke tests below).
- **Root-cause fixes** over local hacks; if a hack is unavoidable, isolate it and call it out in the PR.
- **Respect product boundaries:** this repository is the **CasparCG Server** playout engine. **Bridge** and other control-plane work live in other repos; see [docs/PRD_InHouse_Web_Graphics_System.md](docs/PRD_InHouse_Web_Graphics_System.md) for how Server fits the wider system—do not assume Bridge changes belong here.

---

## Mandatory: SRT / dev smoke (fork)

For any change that touches **FFmpeg producers/consumers, channels, AMCP load/play paths, config parsing, or SRT-related URLs**, treat the fork’s SRT dev loop as **mandatory verification** before calling work done (unless the task explicitly exempts runtime checks).

1. Read **[docs/QUICK_START.md](docs/QUICK_START.md)** for the one-command path; use **[docs/DEV_SETUP.md](docs/DEV_SETUP.md)** for full detail and troubleshooting.
2. **Standard ports in dev config:** AMCP **5250**, media **8000**, SRT input **9000**, monitoring **9001**, consumption **9002** (see QUICK_START).
3. **Typical smoke:** after a successful build/install, run the all-in-one script (or the manual three-step flow), confirm CasparCG starts, SRT input loads via AMCP, and outputs are reachable (e.g. `ffplay` on 9001/9002). Use `./test_srt_connection.sh` and `log/caspar_*.log` as documented when diagnosing.

**Reference config and scripts (when present in the working tree):** `casparcg.dev.config`, `start_dev_setup.sh`, `send_mp4_to_srt.sh`, `load_srt_input.sh`, `test_srt_connection.sh`.

**CEF on Linux:** staging runs should still use **`./run.sh`** where applicable so CEF sees a correct executable path ([BUILDING.md](BUILDING.md) troubleshooting)—this applies alongside the SRT flow, not instead of it.

---

## Optional but recommended

| When | Read / use |
|------|------------|
| Web graphics, HTML templates, CEF, roadmap alignment | [docs/PRD_InHouse_Web_Graphics_System.md](docs/PRD_InHouse_Web_Graphics_System.md) |
| Production images / release process | [docs/PRODUCTION_BUILD.md](docs/PRODUCTION_BUILD.md) (if present) |
| HTML template samples in-tree | [CasparMedia/template/](CasparMedia/template/) (`timer.html`, `lowerthird.html`) |

---

## Repository map (fork-aware)

| Area | Role |
|------|------|
| [src/CMakeLists.txt](src/CMakeLists.txt) | Top-level CMake: version, options (`ENABLE_HTML`, CEF, Boost, etc.), subprojects |
| [src/shell/](src/shell/) | Entry ([main.cpp](src/shell/main.cpp)), server bootstrap, console |
| [src/core/](src/core/) | Channels, producers/consumers pipeline |
| [src/common/](src/common/) | Shared utilities, logging, platform helpers |
| [src/protocol/](src/protocol/) | AMCP and related protocol handling |
| [src/modules/](src/modules/) | FFmpeg, HTML/CEF, Decklink, image, … |
| [src/accelerator/](src/accelerator/) | GPU / GL acceleration |
| [src/CMakeModules/](src/CMakeModules/) | Bootstrap CMake, `CasparCG_Util.cmake` |
| [tools/linux/](tools/linux/) | Linux deps, Docker build, deb packaging |
| [tools/windows/](tools/windows/) | Windows build scripts |
| [.github/workflows/](.github/workflows/) | CI (Linux Docker + deb matrix, Windows) |
| [CasparMedia/](CasparMedia/) | **Fork:** example HTML templates referenced in PRD |

`CMAKE_EXPORT_COMPILE_COMMANDS` is ON for **clangd / IDE** integration.

---

## Tech stack

- **C++17** via CMake (`cxx_std_17` in [src/CMakeModules/CasparCG_Util.cmake](src/CMakeModules/CasparCG_Util.cmake)).
- **Configure** from a **`build/`** directory: `cmake ../src` (source is **`src/`**, not repo root).
- **Deps:** Boost, FFmpeg, SFML, TBB, OpenGL; **CEF** when `ENABLE_HTML` is ON (default).

---

## Build and verify

### Linux (typical agent host: Ubuntu LTS)

```bash
sudo ./tools/linux/install-dependencies
mkdir -p build && cd build
cmake ../src    # add -DENABLE_HTML=OFF if CEF unavailable
cmake --build . --parallel
cmake --install . --prefix staging
```

Run from staging with **`./run.sh`** when using CEF ([BUILDING.md](BUILDING.md)).

**Docker (matches `linux.yml`):** `./tools/linux/build-in-docker`

### Windows

[tools/windows/build.bat](tools/windows/build.bat) — see [.github/workflows/windows.yml](.github/workflows/windows.yml).

### Automated tests

There is **no `ctest` suite** to rely on. **Regression signal = clean configure + full build** plus **mandatory SRT smoke** when the change warrants it (see above).

---

## Fancode review expectations (for humans + agents drafting PRs)

- **Describe** what changed and **why**; link issues or internal tickets when available.
- **Verification:** state OS(s), `cmake` flags if non-default, and outcome of **build** + **SRT smoke** (or explain exemption).
- **Scope:** no unrelated refactors; no new top-level markdown unless the task asked for documentation.
- **Secrets:** never commit API keys, `.env`, or host-specific absolute paths meant only for one machine.
- **Formatting:** [.clang-format](.clang-format) on touched C++ files.
- **Large moves:** dependency upgrades, submodule changes, or CI workflow edits need **explicit maintainer intent**.

---

## Common pitfalls

1. **CEF / relative binary path** on Linux — use `./run.sh` from staging; avoid invoking `bin/casparcg` with a relative `argv[0]` ([BUILDING.md](BUILDING.md)).
2. **GPU / GL** — OpenGL 4.5-class GPU; CI does not catch all runtime GL issues.
3. **CMake downloads** — offline or air-gapped builds: `CASPARCG_DOWNLOAD_CACHE` / `CASPARCG_DOWNLOAD_MIRROR` ([BUILDING.md](BUILDING.md)).
4. **Windows `/WX`** — warnings are errors; fix new warnings from your change.

---

## Where to implement typical tasks

| Task | Likely locations |
|------|------------------|
| Producer/consumer / SRT paths | `src/core/`, `src/modules/ffmpeg/` |
| AMCP | `src/protocol/` |
| Startup, config, logging | `src/shell/`, `src/common/` |
| New module | `src/modules/<name>/` + CMake + module init |
| GPU | `src/accelerator/`, module GL code |
| CI / packaging | `tools/*`, `.github/workflows/` |

---

## Agent checklist

1. Confirm **base branch** (`fc-master` vs `master`) and whether **CI** must run for this change.
2. Read **BUILDING.md** for the OS you build on; read **docs/QUICK_START** and **docs/DEV_SETUP** when touching streaming or AMCP load paths.
3. Mirror **existing** patterns; keep diffs minimal.
4. **Build** (and **SRT smoke** when mandatory).
5. PR text: problem, solution, verification—no drive-by doc dumps.
