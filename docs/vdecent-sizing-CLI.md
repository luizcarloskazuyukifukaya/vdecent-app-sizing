# V-Decent Sizing CLI Tool (vdecent-size) 

## AI Agent Specification & Prompt

### 

# **Document Purpose**

This document serves as an exhaustive, context-rich specification to instruct an AI Coding Agent to build a local application sizing CLI tool for the V-Decent platform. The tool will measure local multi-container application resource footprints and map them directly to V-Decent's standardized hosting tiers.

# **1\. Project Context & Scenario**

V-Decent is a distributed cloud platform designed for micro-entrepreneur developers. To simplify infrastructure management, developers do not manually configure complex hardware resource limits. Instead, they deploy multi-container environments (managed via Docker Compose) under an implicit baseline assumption.  
This CLI tool (vdecent-size) is given directly to developers so they can measure their application's performance profile locally before deploying it to the production grid. The tool attaches to their running local Docker daemon, monitors real-time resource usage during a test window, and computes a standardized scalar score called the **V-Decent Resource Unit (VRU)**.

# **2\. Core Mathematical Architecture**

The AI Agent must implement the following deterministic evaluation formulas exactly:

#### **A. V-Decent Resource Unit (VRU) Formula**

The VRU normalizes CPU and RAM consumption against a baseline small application ('S' Tier), applying a heavy weight to memory.  
$$VRU \= \\left(0.3 \\cdot \\frac{\\text{Avg\\\_CPU\\\_vCPUs}}{0.2}\\right) \+ \\left(0.7 \\cdot \\frac{\\text{Avg\\\_RAM\\\_GB}}{0.5}\\right) \+ \\text{Storage\\\_Penalty}$$

#### **B. Storage Penalty Modifier**

Storage serves as a secondary capacity constraint. If an application stays within its tier's fair-share limit (5 GB scaled by its relative tier size magnitude), the penalty is 0\. Exceeding it scales the score up linearly:  
$$\\text{Storage\\\_Penalty} \= \\max\\left(0, \\frac{\\text{Actual\\\_Storage\\\_GB} \- \\text{Core\\\_Tier\\\_Fair\\\_Share\\\_Storage}}{25}\\right)$$

# **3\. Functional Requirements for the AI Agent**

#### **Requirement 1: Execution Lifecycle Management**

The CLI tool must expose a clean interface with two primary operational workflows:

* vdecent-size profile \--duration \<minutes\>: Launches a telemetry profiling daemon. It must query the local Docker engine API to pull live statistics (docker stats equivalent) for all containers belonging to the target active Docker Compose project.  
* The profile window should capture:  
  * **Average & Peak CPU usage** (transmuted from percentage back into total active fractional vCPUs).  
  * **Average RAM usage** (converted to explicit Gigabytes).  
  * **Total Persistent Storage Footprint** (summing active write layers and mapped volume spaces).

#### **Requirement 2: Tier Categorization Logic**

Upon completion of the profiling window, the script must map the final calculated VRU score into one of the four rigid system brackets:

| Category Size | VRU Score Spectrum | Equivalent 'S' Value | Fair-Share Storage Ceiling |
| :---- | :---- | :---- | :---- |
| **S (Small)** | $0.0 \\le \\text{VRU} \\le 1.2$ | $1\\text{ S}$ | 5 GB |
| **M (Medium)** | $1.2 \< \\text{VRU} \\le 2.4$ | $2\\text{ S}$ | 10 GB |
| **L (Large)** | $2.4 \< \\text{VRU} \\le 4.8$ | $4\\text{ S}$ | 20 GB |
| **XL (Extra Large)** | $\\text{VRU} \> 4.8$ | Custom ($8\\text{S}+$) | Dedicated / Custom |

#### **Requirement 3: Output Generation & Export**

* **Terminal UI:** Output a scannable ASCII dashboard displaying the raw metric averages, the finalized VRU score, and the designated V-Decent Application Tier classification.  
* **Artifact Output:** Write a clean, structured vdecent-tier.json file containing the precise payload data required by the Coolify API configuration endpoint (limits\_cpus, limits\_memory, limits\_memory\_swap: "0m", and limits\_memory\_swappiness: 0).

# **4\. Technical Constraints & Design Rules for Implementation**

* **Language Choice:** Build this using Go (for a single compiled binary distribution without runtime dependencies) or Python 3.11+ (using standard click or argparse libraries).  
* **Docker API Integration:** Utilize the native Docker Engine SDK rather than parsing raw shell strings out of subprocess calls to command-line utilities.  
* **No Swap Assumptions:** Ensure the scoring algorithm treats RAM consumption values purely as physical physical system allocations. It must print a warning if swap usage is discovered active in the local container stack.

# **5\. Expected Prompt Context for the AI Agent**

*"Act as an expert Systems Engineer and Cloud Architect. Build a production-grade CLI tool adhering to the scenario, mathematical formulas, and structural requirements defined above. Provide structured error handling for disconnected Docker daemons or missing Docker Compose context files. Deliver clean, maintainable, modular source code along with instructions for compiling or running the tool locally."*