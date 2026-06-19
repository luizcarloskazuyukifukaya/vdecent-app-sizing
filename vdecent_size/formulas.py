import math
from typing import Dict, Any, Tuple

# Constants based on the V-Decent Platform Blueprint
CPU_BASELINE = 0.2  # vCPU
RAM_BASELINE = 0.5  # GB (512 MB)

TIER_S = "S"
TIER_M = "M"
TIER_L = "L"
TIER_XL = "XL"

# Fair-share storage ceilings for each tier in GB
STORAGE_CEILINGS = {
    TIER_S: 5.0,
    TIER_M: 10.0,
    TIER_L: 20.0,
    TIER_XL: 40.0,  # 8S equivalent baseline
}

# VRU boundaries
VRU_LIMITS = {
    TIER_S: 1.2,
    TIER_M: 2.4,
    TIER_L: 4.8,
}

def calculate_base_vru(avg_cpu: float, avg_ram: float) -> float:
    """
    Calculate VRU score based purely on CPU and RAM, without storage penalty.
    avg_cpu: average CPU usage in vCPUs (fractional cores, e.g. 0.2)
    avg_ram: average RAM usage in GB (e.g. 0.5)
    """
    return (0.3 * (avg_cpu / CPU_BASELINE)) + (0.7 * (avg_ram / RAM_BASELINE))

def calculate_storage_penalty(actual_storage: float, ceiling: float) -> float:
    """
    Calculate the storage penalty for a given actual storage usage and tier ceiling.
    actual_storage: persistent storage footprint in GB
    ceiling: tier's fair-share storage limit in GB
    """
    return max(0.0, (actual_storage - ceiling) / 25.0)

def resolve_tier_and_vru(avg_cpu: float, avg_ram: float, actual_storage: float) -> Tuple[str, float, float]:
    """
    Resolves the correct V-Decent hosting tier and final VRU score.
    Since storage penalty depends on the tier's storage ceiling, we iteratively
    evaluate the tiers from smallest to largest.
    
    Returns:
        Tuple of (tier_name, final_vru, storage_penalty)
    """
    base_vru = calculate_base_vru(avg_cpu, avg_ram)
    
    # 1. Test Tier S
    penalty_s = calculate_storage_penalty(actual_storage, STORAGE_CEILINGS[TIER_S])
    vru_s = base_vru + penalty_s
    if vru_s <= VRU_LIMITS[TIER_S]:
        return TIER_S, vru_s, penalty_s
        
    # 2. Test Tier M
    penalty_m = calculate_storage_penalty(actual_storage, STORAGE_CEILINGS[TIER_M])
    vru_m = base_vru + penalty_m
    if vru_m <= VRU_LIMITS[TIER_M]:
        return TIER_M, vru_m, penalty_m
        
    # 3. Test Tier L
    penalty_l = calculate_storage_penalty(actual_storage, STORAGE_CEILINGS[TIER_L])
    vru_l = base_vru + penalty_l
    if vru_l <= VRU_LIMITS[TIER_L]:
        return TIER_L, vru_l, penalty_l
        
    # 4. Fallback to Tier XL
    penalty_xl = calculate_storage_penalty(actual_storage, STORAGE_CEILINGS[TIER_XL])
    vru_xl = base_vru + penalty_xl
    return TIER_XL, vru_xl, penalty_xl
