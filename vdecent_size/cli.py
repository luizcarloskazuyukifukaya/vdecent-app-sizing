import os
import sys
import json
import click
from typing import Dict, Any
from vdecent_size.profiler import detect_project_name, run_telemetry

# Terminal formatting codes
C_GREEN = "\033[1;32m"
C_YELLOW = "\033[1;33m"
C_RED = "\033[1;31m"
C_CYAN = "\033[1;36m"
C_BOLD = "\033[1m"
C_RESET = "\033[0m"

@click.group()
def main():
    """V-Decent App Sizing CLI Tool."""
    pass

@main.command()
@click.option(
    "--duration",
    type=float,
    required=True,
    help="Duration of the profiling session in minutes (e.g. 1, 5, or 0.1 for 6 seconds)."
)
@click.option(
    "--compose-file",
    "-f",
    type=click.Path(exists=False),
    help="Path to the docker-compose.yml configuration."
)
@click.option(
    "--project-name",
    "-p",
    type=str,
    help="Name of the target Docker Compose project."
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="vdecent-size.json",
    help="Path to write the V-Decent sizing report JSON (defaults to vdecent-size.json)."
)
def profile(duration: float, compose_file: str, project_name: str, output: str):
    """
    Launches telemetry profiling on active local Docker Compose containers.
    Measures CPU, RAM, and Storage to compute VRU score and recommend V-Decent Tier.
    """
    if duration <= 0:
        click.echo(f"{C_RED}Error: Duration must be greater than 0 minutes.{C_RESET}", err=True)
        sys.exit(1)

    duration_seconds = max(1, int(duration * 60))

    # 1. Resolve project
    try:
        proj_name, detected_path = detect_project_name(compose_file, project_name)
    except Exception as e:
        click.echo(f"{C_RED}Error: {e}{C_RESET}", err=True)
        sys.exit(1)

    click.echo(f"{C_CYAN}Target Compose Project:{C_RESET} {C_BOLD}{proj_name}{C_RESET}")
    if detected_path:
        click.echo(f"{C_CYAN}Compose Context File:{C_RESET} {detected_path}")
    click.echo(f"{C_CYAN}Telemetry Window:{C_RESET} {duration} minutes ({duration_seconds} seconds)")
    click.echo(f"Initializing telemetry stream from local Docker Daemon...")

    # 2. Run telemetry loop
    try:
        telemetry_gen = run_telemetry(proj_name, duration_seconds)
        last_progress = None
        
        for update in telemetry_gen:
            if update["status"] == "profiling":
                tick = update["tick"]
                total = update["total_ticks"]
                percent = int((tick / total) * 100)
                bar_len = 25
                filled_len = int(bar_len * tick // total)
                bar = "=" * filled_len + ">" + " " * (bar_len - filled_len - 1)
                if tick == total:
                    bar = "=" * bar_len
                
                # Single-line status update
                sys.stdout.write(
                    f"\rProfiling [{C_GREEN}{bar}{C_RESET}] {percent}% "
                    f"(Tick {tick}/{total}) - CPU: {update['current_cpu']:.2f} vCPUs | RAM: {update['current_ram']:.2f} GB"
                )
                sys.stdout.flush()
            elif update["status"] == "complete":
                last_progress = update
        
        sys.stdout.write("\n")
        sys.stdout.flush()
    except Exception as e:
        sys.stdout.write("\n")
        click.echo(f"{C_RED}Error during telemetry collection: {e}{C_RESET}", err=True)
        sys.exit(1)

    if not last_progress:
        click.echo(f"{C_RED}Error: Telemetry execution did not produce final results.{C_RESET}", err=True)
        sys.exit(1)

    # 3. Output beautiful ASCII report
    avg_cpu = last_progress["avg_cpu_vcpus"]
    peak_cpu = last_progress["peak_cpu_vcpus"]
    avg_ram = last_progress["avg_ram_gb"]
    peak_ram = last_progress["peak_ram_gb"]
    storage = last_progress["storage_gb"]
    penalty = last_progress["storage_penalty"]
    final_vru = last_progress["final_vru"]
    tier = last_progress["tier"]
    swap_active = last_progress["swap_active"]
    max_swap = last_progress["max_swap_gb"]
    
    # Calculate base VRU for reference
    base_vru = final_vru - penalty

    vru_status = "OPTIMAL"
    status_color = C_GREEN
    
    click.echo("=" * 80)
    click.echo(f"                      {C_BOLD}V-DECENT APPLICATION SIZING REPORT{C_RESET}")
    click.echo("=" * 80)
    click.echo(f" {C_BOLD}Project:{C_RESET}         {proj_name}")
    click.echo(f" {C_BOLD}Resolved Size:{C_RESET}   {C_CYAN}{tier}{C_RESET}")
    click.echo(f" {C_BOLD}Final Score:{C_RESET}     {status_color}{final_vru:.2f} VRU{C_RESET}")
    click.echo(f" {C_BOLD}Status:{C_RESET}          {status_color}{vru_status}{C_RESET}")
    click.echo("-" * 80)
    click.echo(f" {C_BOLD}TELEMETRY RESULTS (Duration: {duration}m across {last_progress['containers_count']} containers){C_RESET}")
    click.echo("-" * 80)
    click.echo(f"   {"RESOURCE":<16} {"AVERAGE":<18} {"PEAK":<18}")
    click.echo("  " + "-" * 76)
    click.echo(f"   CPU (vCPUs)      {avg_cpu:<18.2f} {peak_cpu:<18.2f}")
    click.echo(f"   Memory (RAM GB)  {avg_ram:<18.2f} {peak_ram:<18.2f}")
    click.echo(f"   Storage (Disk GB){storage:<18.2f} {"-":<18}")
    click.echo("  " + "-" * 76)
    click.echo(f"   Storage Penalty: {C_YELLOW}{penalty:.2f} VRU{C_RESET} (Calculated from: max(0, (Actual_Storage_GB - Core_Tier_Fair_Share_Storage) / 25))")
    click.echo(f"   Base VRU Score:  {base_vru:.2f} VRU")
    click.echo(f"   Final VRU Score: {C_BOLD}{final_vru:.2f} VRU{C_RESET}")
    click.echo("=" * 80)
    click.echo(f" {C_BOLD}DEPLOYMENT INSTRUCTIONS (V-Decent Application Manager){C_RESET}")
    click.echo("=" * 80)
    click.echo(f"   When deploying this application using the V-Decent Application Manager,")
    click.echo(f"   please specify the application size as: {C_GREEN}{C_BOLD}{tier}{C_RESET}")
    click.echo("")
    click.echo(f"   Note: If the application performance is not optimal under real-world")
    click.echo(f"   workloads, it is recommended to increase the size to the next tier.")
    click.echo("")
    click.echo(f" {C_YELLOW}{C_BOLD}DISCLAIMER:{C_RESET}")
    click.echo(f"   The result of this application sizing is based on the local test performed")
    click.echo(f"   and does not necessarily reflect the real production usage environment.")
    click.echo(f"   Depending on actual production usage, the required application size could")
    click.echo(f"   change (mostly should be increased), as profiling is typically conducted")
    click.echo(f"   with minimum resource usage.")
    click.echo("=" * 80)
    
    if swap_active:
        click.echo(f" {C_RED}{C_BOLD}WARNINGS & ALERTS:{C_RESET}")
        click.echo(f"   {C_YELLOW}[!] ACTIVE SWAP CONFIGURATION OR USAGE DETECTED{C_RESET}")
        click.echo(f"       Containers in this compose project are configured with swap enabled, or")
        click.echo(f"       real-time swap usage was recorded (Max: {max_swap:.2f} GB).")
        click.echo(f"       This violates the strict V-Decent no-swap production architecture rules,")
        click.echo(f"       which can degrade cluster scheduling stability and hide OOM events.")
        click.echo("=" * 80)

    # 4. Write export file
    output_data = {
        "project_name": proj_name,
        "duration_minutes": duration,
        "avg_cpu_vcpus": round(avg_cpu, 4),
        "peak_cpu_vcpus": round(peak_cpu, 4),
        "avg_ram_gb": round(avg_ram, 4),
        "peak_ram_gb": round(peak_ram, 4),
        "storage_gb": round(storage, 4),
        "storage_penalty": round(penalty, 4),
        "vru_score": round(final_vru, 4),
        "deterministic_size": tier,
        "disclaimer": (
            "The result of this application sizing is based on the local test performed "
            "and does not necessarily reflect the real production usage environment. "
            "Depending on actual production usage, the required application size could "
            "change (mostly should be increased), as profiling is typically conducted "
            "with minimum resource usage."
        )
    }
    
    try:
        with open(output, "w") as f:
            json.dump(output_data, f, indent=4)
        click.echo(f"{C_GREEN}Sizing report written successfully to {output}.{C_RESET}")
    except Exception as e:
        click.echo(f"{C_RED}Failed to write sizing report: {e}{C_RESET}", err=True)

if __name__ == "__main__":
    main()
