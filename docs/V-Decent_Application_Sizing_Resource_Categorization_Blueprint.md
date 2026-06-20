# **V-Decent Platform: Application Sizing and Resource Categorization Blueprint**

This document outlines the architectural blueprint for managing, sizing, and pricing applications deployed across the V-Decent distributed node network. By leveraging a deterministic scoring framework based on historical telemetry, the platform abstractly categorizes multi-container environments (Docker Compose) without imposing manual configuration burdens on micro-entrepreneur developers.

# **Design**

## **1\. System Baseline & Minimum Node Specifications**

The infrastructure design anchors its initial resource distribution assumptions on a standardized hardware node baseline. System thresholds and scheduling density metrics are calculated using these constraints:

* **Minimum Node Specification:** 4 vCPUs, 8 GB RAM, 125 GB Storage.  
* **Primary Resource Bottleneck:** RAM (System Memory). While CPU usage can be softly throttled during spikes, RAM exhaustion triggers critical operating system Out-Of-Memory (OOM) processes. Therefore, RAM acts as the strict capacity ceiling.  
* **The 'S' Size Reference Baseline:** Defined as a standard low-footprint application, such as a static business website containing up to 10 pages paired with a single lightweight database instance.

| Resource Type | Baseline 'S' Allocation | Minimum Node Physical Limit | Max Theoretical Capacity (Per Node)   |
| :---- | :---- | :---- | :---- |
| **CPU** | 0.2 vCPU (20% of a single core) | 4 vCPUs | 20 Applications |
| **RAM** | 512 MB (0.5 GB) | 8 GB | 16 Applications |
| **Storage** | 5 GB (Secondary constraint) | 125 GB | 25 Applications |

*Resulting Allocation Ceiling:* Because RAM enforces the lowest common denominator, a baseline node running at 100% capacity safely hosts exactly **16 'S' size applications**.

## **2\. Unified Scoring Model: V-Decent Resource Unit (VRU)**

To facilitate long-term platform extensibility and automated hosting tier evaluations, resource consumption is condensed into a singular scalar value known as the **V-Decent Resource Unit (VRU)**. This unified formula applies a heavy weight to RAM capacity while leaving room for storage penalties if an application over-allocates disk footprint.  
The formula is normalized so that an application matching the exact 'S' resource baseline yields a score of exactly **1.0 VRU**:

VRU \= (0.3 \* (Avg\_CPU\_vCPUs / 0.2)) \+ (0.7 \* (Avg\_RAM\_GB / 0.5)) \+ Storage\_Penalty

### **Handling the Storage Penalty Modifer**

Storage functions as a secondary constraint. If an application utilizes storage within its fair-share tier limit (5 GB multiplied by its scaling magnitude), the penalty is 0\. If it exceeds this footprint, the VRU increases proportionally to reflect the physical disk overhead:

Storage\_Penalty \= Max(0, (Actual\_Storage\_GB \- Core\_Tier\_Fair\_Share\_Storage) / 25\)

## **3\. Size Categories & Capacity Tiers**

Applications automatically transition between tiers based on their computed monthly rolling VRU average. These categories map cleanly into scheduling weights and serve as the baseline index for hosting pricing models.

| Category Size | VRU Score Spectrum | Equivalent 'S' Value | Max Density (Per Minimum Node)   |
| :---- | :---- | :---- | :---- |
| **S (Small)** | 0.0 ≤ VRU ≤ 1.2 | 1 S | 16 Apps |
| **M (Medium)** | 1.2 \< VRU ≤ 2.4 | 2 S | 8 Apps |
| **L (Large)** | 2.4 \< VRU ≤ 4.8 | 4 S | 4 Apps |
| **XL (Extra Large)** | VRU \> 4.8 | Custom (8S+) | Dedicated / Specialized Placement |

## **4\. Node-Level Scheduling & Overcommit Guardrails**

The orchestrator balances cluster workload using a \+10% maximum overcommit margin to optimize cluster density without risking physical hardware node failure.

* **Target Node Rating:** 16.0 VRUs maximum.  
* **Hard Overcommit Capacity (+10%):** 17.6 VRUs maximum. The node scheduler completely rejects incoming application deployments if the node's collective VRU score breaches 17.6.

# **Implementation**

To implement the resource limits based on the V-Decent blueprint within your Coolify deployment pipeline, you can utilize the Coolify API to programmatically enforce resource constraints at the application level.  
Because Coolify acts as a management layer over Docker, specifying these limits via its API directly translates into underlying Docker resource constraints (e.g., \--cpus and \--memory).  
Here is a comprehensive implementation guide to map your V-Decent architecture blueprint to Coolify.

## **1\. Resource Mapping Table (Blueprint to Coolify)**

To ensure applications do not breach their physical node capacity or disrupt cluster density, you must translate the V-Decent sizing tiers into explicit hardware limits.  
The baseline S tier is allocated **0.2 vCPU** and **512 MB RAM**. Since RAM is your strict capacity ceiling , the limits below scale proportionally based on the Equivalent 'S' Value:

| Category Size | Equivalent 'S' Value Google Docs | Coolify CPU Limit (limits\_cpus) | Coolify RAM Limit (limits\_memory) |
| :---- | :---- | :---- | :---- |
| **S (Small)** | 1 S | 0.2 | 512m |
| **M (Medium)** | 2 S | 0.4 | 1024m (1 GB) |
| **L (Large)** | 4 S | 0.8 | 2048m (2 GB) |
| **XL (Extra Large)** | 8S+ (Custom) | 1.6\+ | 4096m\+ (Custom) |

**Note on Storage:** While your blueprint defines a fair-share storage baseline (e.g., 5 GB for size S), Coolify / Docker standard resource limits do not natively enforce strict disk capacity quotas per container on standard file systems. Storage constraints should continue to be monitored via your Application Manager (AM) telemetry to apply the Storage\_Penalty to the VRU score.

## **2\. Coolify API Implementation Details**

When registering or updating an application in Coolify via the API, resource limits are passed in the request body using the limits\_cpus and limits\_memory parameters.

### **Endpoint**

* **Method:** PATCH or POST  
* **URL:** https://\<your-coolify-instance\>/api/v1/applications/\<application\_uuid\>  
* **Headers:** \* Authorization: Bearer \<your\_api\_token\>  
  * Content-Type: application/json

### **Payload Example: Registering / Updating a Size 'M' Application**

JSON  
{  
  "name": "v-decent-app-prod",  
  "limits\_cpus": "0.4",  
  "limits\_memory": "1024m",  
  "limits\_memory\_swap": "0m",  
  "limits\_memory\_swappiness": 0  
}

**Important Architecture Safeguard:** Set limits\_memory\_swap to "0m" and limits\_memory\_swappiness to 0. If swap space is permitted, an application exceeding its RAM allocation will dump data to disk swap instead of triggering an immediate telemetry or OOM event, hiddenly degrading performance and breaking your strict RAM-based VRU calculations.
