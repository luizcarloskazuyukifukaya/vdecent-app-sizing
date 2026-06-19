# Development Plan: V-Decent Sizing CLI Tool (`vdecent-size`)

This document tracks the execution phases and progress of developing the `vdecent-size` command-line utility.

## 📋 Objective
Build a local application sizing CLI tool in Python 3.11+ that:
1. Connects to the local Docker daemon.
2. Identifies containers belonging to a target Docker Compose project.
3. Profiles real-time CPU (vCPUs), RAM (GB), and persistent storage (write layers + volumes) over a specified time window.
4. Computes the **V-Decent Resource Unit (VRU)** score and maps it to a hosting tier (S, M, L, XL).
5. Exposes a CLI command `vdecent-size profile --duration <minutes>`.
6. Generates a sizing report file `vdecent-size.json` containing the deterministic size (S, M, L, XL).
7. Instructs developers to refer to this sizing result when deploying on V-Decent Application Manager.

---

## 🗺️ Phases & Tasks

### Phase 1: Environment & Setup
- [x] Initialize Python project structure.
- [x] Create `pyproject.toml` or `setup.py` defining package metadata, entry points, and dependencies.
- [x] List dependencies: `click` (CLI framework), `docker` (Docker SDK for Python), `PyYAML` (YAML parsing).
- [x] Create a virtual environment and verify python/pip operations.

### Phase 2: Mathematical Scoring Core
- [x] Implement mathematical formulas in `vdecent_size/formulas.py`:
  - **VRU Formula**: $VRU = (0.3 \cdot \frac{\text{Avg CPU (vCPUs)}}{0.2}) + (0.7 \cdot \frac{\text{Avg RAM (GB)}}{0.5}) + \text{Storage Penalty}$
  - **Storage Penalty**: $\text{Storage Penalty} = \max(0, \frac{\text{Actual Storage (GB)} - \text{Core Tier Fair-Share Storage}}{25})$
  - **Tier Mapping Logic** (S: VRU $\le 1.2$, M: $1.2 < \text{VRU} \le 2.4$, L: $2.4 < \text{VRU} \le 4.8$, XL: $\text{VRU} > 4.8$).
- [x] Write unit tests for formulas to ensure 100% mathematical correctness.

### Phase 3: Docker Telemetry Profiler
- [x] Implement `vdecent_size/profiler.py` using the Docker SDK:
  - Compose project name auto-detection (labels: `com.docker.compose.project`, or parsing `--compose-file`).
  - Active containers filtering.
  - Periodic statistics polling:
    - Real-time CPU usage: convert system/container CPU deltas into active fractional vCPUs.
    - Real-time RAM usage: working set size calculation (`usage - cache`).
    - Swap usage warning: check for container configuration (`MemorySwap`) and real-time swap stats.
  - Storage calculation:
    - Container write layers size (`SizeRw` via `container.inspect(size=True)`).
    - Host-side persistent storage sizes for all unique mapped volumes and bind mounts.

### Phase 4: CLI Interface & Terminal Dashboard
- [x] Implement `vdecent_size/cli.py` with Click.
- [x] Implement `vdecent-size profile --duration <minutes>` command.
- [x] Build a sleek ASCII dashboard to display:
  - Raw telemetry averages (Avg/Peak CPU, RAM, Storage, Swap alerts).
  - Computed VRU score and storage penalties.
  - Finalized V-Decent hosting tier.

### Phase 5: Developer Instructions & Report Formatting
- [x] Expose deterministic size (S, M, L, XL) in terminal dashboard and JSON output file.
- [x] Provide clear instructions for developers on using this sizing as a reference in V-Decent Application Manager.
- [x] Document recommendation for manual sizing upgrades in case of suboptimal performance.

### Phase 6: Integration Testing & Verification
- [x] Build a mock Docker Compose project in the workspace to run validation tests.
- [x] Run profiling over short durations (e.g., 0.1 minutes or 10 seconds) to verify statistics capture.
- [x] Test edge cases (no docker daemon, invalid compose path).

### Phase 7: Final Documentation
- [x] Create `README.md` detailing:
  - Project objectives.
  - Commands and options.
  - Math logic & Tier mappings.
  - V-Decent Application Manager deployment workflow guidelines.

---

## 📈 Current Status
- [x] Phase 1: Environment & Setup (Completed)
- [x] Phase 2: Mathematical Scoring Core (Completed)
- [x] Phase 3: Docker Telemetry Profiler (Completed)
- [x] Phase 4: CLI Interface & Terminal Dashboard (Completed)
- [x] Phase 5: Developer Instructions & Report Formatting (Completed)
- [x] Phase 6: Integration Testing & Verification (Completed)
- [x] Phase 7: Final Documentation (Completed)
