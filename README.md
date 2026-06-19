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
  $$VRU = \left(0.3 \cdot \frac{\text{Avg\_CPU\_vCPUs}}{0.2}\right) + \left(0.7 \cdot \frac{\text{Avg\_RAM\_GB}}{0.5}\right) + \text{Storage\_Penalty}$$
- **Storage Penalty**:
  $$\text{Storage\_Penalty} = \max\left(0, \frac{\text{Actual\_Storage\_GB} - \text{Core\_Tier\_Fair\_Share\_Storage}}{25}\right)$$

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
2. Initialize virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```

### Running Telemetry Profiler
Profile a running docker-compose stack for 1 minute:
```bash
vdecent-size profile --duration 1
```

### 🛰️ V-Decent Application Manager Reference
When deploying your application using the V-Decent Application Manager, you must specify the sizing parameters based on the output of this CLI tool. 
- Refer to the output of `vdecent-size.json` or the terminal report which contains the deterministic size (`S`, `M`, `L`, or `XL`).
- If you experience performance issues, it is recommended to increase the size manually in the V-Decent Application Manager config UI.

> [!IMPORTANT]
> **Disclaimer**: The result of this application sizing is based on the test performed and does not necessarily reflect the real production usage environment. Depending on production usage, the required application size could change (mostly should be increased), as profiling tests are typically conducted with minimum resource usage.
