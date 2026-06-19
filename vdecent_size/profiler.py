import os
import time
import math
import yaml
import docker
from typing import List, Dict, Any, Tuple, Set
from concurrent.futures import ThreadPoolExecutor
from vdecent_size.formulas import resolve_tier_and_vru

def get_dir_size(path: str) -> int:
    """Calculate total size of a host directory in bytes."""
    total_size = 0
    if not os.path.exists(path):
        return 0
    if os.path.isfile(path):
        return os.path.getsize(path)
    try:
        for dirpath, _, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    try:
                        total_size += os.path.getsize(fp)
                    except (OSError, FileNotFoundError):
                        pass
    except Exception:
        pass
    return total_size

def get_volume_size_via_container(client: docker.DockerClient, volume_name: str) -> int:
    """
    Query the size of a named volume using a temporary lightweight Alpine container.
    This avoids permission issues on the host `/var/lib/docker` directory.
    """
    try:
        # Run alpine container, mount the volume, run du -sk /volume_data
        output = client.containers.run(
            "alpine:latest",
            command="du -sk /volume_data",
            volumes={volume_name: {"bind": "/volume_data", "mode": "ro"}},
            remove=True,
            stderr=False
        )
        # Parse output like: "12345\t/volume_data\n"
        decoded = output.decode("utf-8").strip()
        if decoded:
            parts = decoded.split()
            if parts and parts[0].isdigit():
                # Convert KiB to bytes
                return int(parts[0]) * 1024
    except Exception:
        pass
    return 0

def detect_project_name(compose_file: str = None, project_name: str = None) -> Tuple[str, str]:
    """
    Determines the Docker Compose project name and returns (project_name, compose_file_path).
    If project_name is provided, it uses that.
    If compose_file is provided, it reads the project name from it or its parent directory.
    If neither, it searches the current directory. If not found, it lists running compose projects.
    """
    client = docker.from_env()
    
    if project_name:
        return project_name, compose_file or ""
        
    if compose_file:
        if not os.path.exists(compose_file):
            raise FileNotFoundError(f"Specified compose file not found: {compose_file}")
        with open(compose_file, "r") as f:
            try:
                data = yaml.safe_load(f) or {}
            except Exception as e:
                raise ValueError(f"Failed to parse compose file {compose_file}: {e}")
        p_name = data.get("name")
        if not p_name:
            # Default to lowercase parent directory name
            p_name = os.path.basename(os.path.dirname(os.path.abspath(compose_file))).lower()
        return p_name, os.path.abspath(compose_file)

    # Search current directory
    candidates = ["compose.yaml", "compose.yml", "docker-compose.yaml", "docker-compose.yml"]
    for c in candidates:
        if os.path.exists(c):
            with open(c, "r") as f:
                try:
                    data = yaml.safe_load(f) or {}
                    p_name = data.get("name")
                    if not p_name:
                        p_name = os.path.basename(os.getcwd()).lower()
                    return p_name, os.path.abspath(c)
                except Exception:
                    pass

    # Detect running projects from active containers
    running_projects = set()
    for container in client.containers.list():
        proj = container.labels.get("com.docker.compose.project")
        if proj:
            running_projects.add(proj)

    if len(running_projects) == 1:
        p_name = list(running_projects)[0]
        return p_name, ""
    elif len(running_projects) > 1:
        proj_list = ", ".join(sorted(running_projects))
        raise ValueError(
            f"Multiple running Docker Compose projects detected: [{proj_list}].\n"
            "Please specify the target project using --project-name (-p) or --compose-file (-f)."
        )
    else:
        raise ValueError(
            "No active Docker Compose project detected in current directory and no running projects found.\n"
            "Please run this command in a Docker Compose project directory, or start the containers first."
        )

def calculate_cpu_vcpus(stats: dict, prev_stats: dict) -> float:
    """Calculate fractional vCPU usage based on CPU delta and System CPU delta."""
    if not stats or not prev_stats:
        return 0.0
        
    cpu_usage = stats.get("cpu_stats", {}).get("cpu_usage", {}).get("total_usage", 0)
    system_cpu = stats.get("cpu_stats", {}).get("system_cpu_usage", 0)
    
    prev_cpu_usage = prev_stats.get("cpu_stats", {}).get("cpu_usage", {}).get("total_usage", 0)
    prev_system_cpu = prev_stats.get("cpu_stats", {}).get("system_cpu_usage", 0)
    
    cpu_delta = cpu_usage - prev_cpu_usage
    system_delta = system_cpu - prev_system_cpu
    
    if system_delta <= 0 or cpu_delta <= 0:
        return 0.0
        
    online_cpus = stats.get("cpu_stats", {}).get("online_cpus")
    if not online_cpus:
        percpu = stats.get("cpu_stats", {}).get("cpu_usage", {}).get("percpu_usage")
        online_cpus = len(percpu) if percpu else os.cpu_count() or 1
        
    return (cpu_delta / system_delta) * online_cpus

def calculate_ram_gb(stats: dict) -> float:
    """Calculate RAM working set usage in GB (Usage - Cache/Inactive File)."""
    if not stats:
        return 0.0
    mem_stats = stats.get("memory_stats", {})
    usage = mem_stats.get("usage", 0)
    
    stats_detail = mem_stats.get("stats", {})
    cache = stats_detail.get("cache", 0)
    if not cache:
        cache = stats_detail.get("inactive_file", 0)
        
    working_set = usage - cache
    return max(0.0, working_set / (1024 ** 3))

def check_swap_active(container: Any, stats: dict) -> Tuple[bool, float]:
    """
    Checks if swap is active either in configuration (HostConfig) or currently in use (stats).
    Returns (swap_is_active, current_swap_usage_gb).
    """
    # Check config
    host_config = container.attrs.get("HostConfig", {})
    mem_limit = host_config.get("Memory", 0)
    mem_swap_limit = host_config.get("MemorySwap", 0)
    
    # If MemorySwap is -1, swap is unlimited. If MemorySwap > Memory, swap is enabled.
    config_swap = False
    if mem_swap_limit == -1 or (mem_swap_limit > mem_limit and mem_limit > 0):
        config_swap = True
        
    # Check stats for active usage
    mem_stats = stats.get("memory_stats", {})
    stats_detail = mem_stats.get("stats", {})
    
    # In cgroups v1, stats swap is in bytes. In cgroups v2, swap is also sometimes available.
    swap_usage_bytes = stats_detail.get("swap", 0)
    if not swap_usage_bytes:
        # Check alternative swap keys
        swap_usage_bytes = stats_detail.get("swap_usage", 0)
        
    swap_usage_gb = max(0.0, swap_usage_bytes / (1024 ** 3))
    
    return (config_swap or swap_usage_gb > 0.0), swap_usage_gb

def calculate_project_storage(client: docker.DockerClient, containers: List[Any]) -> Tuple[float, List[Dict[str, Any]]]:
    """
    Calculates total persistent storage footprint in GB (write layers + unique volumes/bind mounts).
    Returns (total_storage_gb, details_list).
    """
    total_bytes = 0
    seen_volumes = set()
    seen_binds = set()
    details = []
    
    for container in containers:
        # 1. Container Write Layer
        try:
            # size=True is required to get SizeRw
            inspected = client.api.inspect_container(container.id)
            write_layer_bytes = inspected.get("SizeRw", 0)
        except Exception:
            write_layer_bytes = 0
            
        total_bytes += write_layer_bytes
        details.append({
            "name": container.name,
            "type": "write_layer",
            "source": container.name,
            "size_gb": write_layer_bytes / (1024 ** 3)
        })
        
        # 2. Mounts (Volumes and Binds)
        mounts = container.attrs.get("Mounts", [])
        for mount in mounts:
            m_type = mount.get("Type")
            source = mount.get("Source")
            name = mount.get("Name")
            
            if m_type == "bind":
                if source not in seen_binds:
                    seen_binds.add(source)
                    size = get_dir_size(source)
                    total_bytes += size
                    details.append({
                        "name": os.path.basename(source) or source,
                        "type": "bind_mount",
                        "source": source,
                        "size_gb": size / (1024 ** 3)
                    })
            elif m_type == "volume":
                if name not in seen_volumes:
                    seen_volumes.add(name)
                    # Try host directory first
                    mountpoint = mount.get("Driver")
                    size = 0
                    try:
                        vol = client.volumes.get(name)
                        mp = vol.attrs.get("Mountpoint")
                        if mp and os.path.exists(mp) and os.access(mp, os.R_OK):
                            size = get_dir_size(mp)
                        else:
                            # Use helper container
                            size = get_volume_size_via_container(client, name)
                    except Exception:
                        size = get_volume_size_via_container(client, name)
                        
                    total_bytes += size
                    details.append({
                        "name": name,
                        "type": "volume",
                        "source": name,
                        "size_gb": size / (1024 ** 3)
                    })
                    
    return total_bytes / (1024 ** 3), details

def poll_all_stats(containers: List[Any]) -> Dict[str, dict]:
    """Poll stats for all containers concurrently using a ThreadPoolExecutor."""
    results = {}
    def poll_one(c):
        try:
            return c.id, c.stats(stream=False)
        except Exception:
            return c.id, {}

    with ThreadPoolExecutor(max_workers=len(containers) or 1) as executor:
        for cid, stats in executor.map(poll_one, containers):
            results[cid] = stats
            
    return results

def run_telemetry(project_name: str, duration_seconds: int):
    """
    Runs the telemetry collection loop for the specified duration.
    Yields status dictionaries at each second.
    """
    client = docker.from_env()
    
    # 1. Get containers
    containers = client.containers.list(filters={"label": f"com.docker.compose.project={project_name}"})
    if not containers:
        raise ValueError(f"No running containers found for project: {project_name}")
        
    # 2. Get initial stats for CPU baseline
    prev_stats = poll_all_stats(containers)
    time.sleep(1)
    
    cpu_history = []
    ram_history = []
    swap_warnings = False
    max_swap_gb = 0.0
    
    # Track metrics per container
    container_cpu_sums = {c.id: 0.0 for c in containers}
    container_ram_sums = {c.id: 0.0 for c in containers}
    container_ticks = {c.id: 0 for c in containers}
    
    for tick in range(1, duration_seconds + 1):
        current_stats = poll_all_stats(containers)
        
        tick_cpu_total = 0.0
        tick_ram_total = 0.0
        
        for c in containers:
            c_stats = current_stats.get(c.id, {})
            c_prev = prev_stats.get(c.id, {})
            
            if not c_stats:
                continue
                
            # CPU
            vcpus = calculate_cpu_vcpus(c_stats, c_prev)
            tick_cpu_total += vcpus
            container_cpu_sums[c.id] += vcpus
            
            # RAM
            ram_gb = calculate_ram_gb(c_stats)
            tick_ram_total += ram_gb
            container_ram_sums[c.id] += ram_gb
            
            container_ticks[c.id] += 1
            
            # Swap
            swap_active, swap_gb = check_swap_active(c, c_stats)
            if swap_active:
                swap_warnings = True
            if swap_gb > max_swap_gb:
                max_swap_gb = swap_gb
                
        cpu_history.append(tick_cpu_total)
        ram_history.append(tick_ram_total)
        
        # Save current stats as previous for next tick
        prev_stats = current_stats
        
        # Yield current tick status for UI update
        yield {
            "status": "profiling",
            "tick": tick,
            "total_ticks": duration_seconds,
            "current_cpu": tick_cpu_total,
            "current_ram": tick_ram_total,
            "swap_active": swap_warnings
        }
        
        if tick < duration_seconds:
            time.sleep(1)
            
    # Calculate final averages
    final_avg_cpu = 0.0
    final_avg_ram = 0.0
    for c in containers:
        ticks = container_ticks[c.id]
        if ticks > 0:
            final_avg_cpu += container_cpu_sums[c.id] / ticks
            final_avg_ram += container_ram_sums[c.id] / ticks
            
    # Peak is the maximum sum of CPU/RAM observed at any tick
    peak_cpu = max(cpu_history) if cpu_history else 0.0
    peak_ram = max(ram_history) if ram_history else 0.0
    
    # Storage
    storage_gb, storage_details = calculate_project_storage(client, containers)
    
    # Resolve tier and final VRU
    tier, final_vru, penalty = resolve_tier_and_vru(final_avg_cpu, final_avg_ram, storage_gb)
    
    yield {
        "status": "complete",
        "project_name": project_name,
        "containers_count": len(containers),
        "avg_cpu_vcpus": final_avg_cpu,
        "peak_cpu_vcpus": peak_cpu,
        "avg_ram_gb": final_avg_ram,
        "peak_ram_gb": peak_ram,
        "storage_gb": storage_gb,
        "storage_details": storage_details,
        "swap_active": swap_warnings,
        "max_swap_gb": max_swap_gb,
        "final_vru": final_vru,
        "storage_penalty": penalty,
        "tier": tier
    }
