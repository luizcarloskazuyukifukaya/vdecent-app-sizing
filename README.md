# V-Decent Sizing CLI Tool (`vdecent-size`)

The `vdecent-size` CLI tool allows V-Decent developers to measure the resource footprint of multi-container applications (Docker Compose) locally before deployment. It calculates a unified score called the **V-Decent Resource Unit (VRU)**, maps the application to a standardized V-Decent hosting tier, and exports a `vdecent-size.json` sizing report.

## 🎯 Project Objective
Simplify cluster orchestration and capacity planning by ensuring container limits are mapped to deterministic scoring metrics based on empirical local execution telemetry.

## 🛠️ Functions
- **`profile`**: Attaches to the local Docker daemon, pulls real-time stats for a target Docker Compose project, averages usage, computes the VRU, resolves the hosting tier size, and exports the result.

## 🧪 Math & Tier Specification
- **CPU (vCPUs)**: Averaged over the duration window.
- **RAM (GB)**: Working set memory (`Memory - Cache`) averaged.
- **Storage (GB)**: Sum of container read-write layers and unique volume host directories.
- **VRU Score Formula**:
  $$VRU = \left(0.3 \cdot \frac{\text{Avg CPU (vCPUs)}}{0.2}\right) + \left(0.7 \cdot \frac{\text{Avg RAM (GB)}}{0.5}\right) + \text{Storage Penalty}$$
- **Storage Penalty**:
  $$\text{Storage Penalty} = \max\left(0, \frac{\text{Actual Storage (GB)} - \text{Core Tier Fair-Share Storage}}{25}\right)$$

### Tier Thresholds

| Tier | VRU Range | CPU Limit Reference | RAM Limit Reference | Fair-Share Storage |
|:---|:---|:---|:---|:---|
| **S (Small)** | $0.0 \le \text{VRU} \le 1.2$ | 0.2 vCPU | 512 MB | 5 GB |
| **M (Medium)** | $1.2 < \text{VRU} \le 2.4$ | 0.4 vCPU | 1024 MB | 10 GB |
| **L (Large)** | $2.4 < \text{VRU} \le 4.8$ | 0.8 vCPU | 2048 MB | 20 GB |
| **XL (Extra Large)**| $\text{VRU} > 4.8$ | 1.6+ vCPU | 4096+ MB | Custom |

## 🚀 How to Test Locally

### Prerequisites
- Python 3.11+
- Running Docker daemon and `docker compose`
- Valid Docker Compose project running locally

### Installation
1. Clone this repository.
   ```bash
   git clone https://github.com/luizcarloskazuyukifukaya/vdecent-app-sizing
   ```

2. Initialize virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```

### Running Telemetry Profiler
There are three ways to execute the profiler on your target application stack:

#### Option A: Running from the target project directory (Auto-detection)
Activate the virtual environment where the tool is installed, navigate (`cd`) to your target project folder (which contains the compose file), and run the tool. It will auto-detect the configuration:
```bash
# 1. Activate the environment from the tool's install directory
cd ~/projects/vdecent-app-sizing
source .venv/bin/activate

# 2. Navigate to your target project and run
cd ~/projects/Andreia-online-store
vdecent-size profile --duration 1
```

#### Option B: Specifying the Compose File path
Execute the tool from any directory by pointing directly to the target project's compose configuration file:
```bash
vdecent-size profile --duration 1 --compose-file ~/projects/Andreia-online-store/docker-compose.yml
```

#### Option C: Specifying the Project Name (For already running stacks)
If the target project's docker-compose containers are already active, you can profile them from any directory by passing its compose project name (e.g. check running project labels via `docker ps`):
```bash
vdecent-size profile --duration 1 --project-name andreia-online-store
```

### 🛰️ V-Decent Application Manager Reference
When deploying your application using the V-Decent Application Manager, you must specify the sizing parameters based on the output of this CLI tool. 
- Refer to the output of `vdecent-size.json` or the terminal report which contains the deterministic size (`S`, `M`, `L`, or `XL`).
- If you experience performance issues, it is recommended to increase the size manually in the V-Decent Application Manager config UI.

> [!IMPORTANT]
> **Disclaimer**: The result of this application sizing is based on the test performed and does not necessarily reflect the real production usage environment. Depending on production usage, the required application size could change (mostly should be increased), as profiling tests are typically conducted with minimum resource usage.
