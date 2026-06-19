import unittest
from unittest.mock import MagicMock, patch
import os
import tempfile
import yaml
from vdecent_size.profiler import (
    calculate_cpu_vcpus,
    calculate_ram_gb,
    check_swap_active,
    detect_project_name,
    get_dir_size
)

class TestProfilerMetrics(unittest.TestCase):
    def test_calculate_cpu_vcpus(self):
        # Setup mock stats dictionaries
        stats = {
            "cpu_stats": {
                "cpu_usage": {"total_usage": 200000000},
                "system_cpu_usage": 1000000000,
                "online_cpus": 4
            }
        }
        prev_stats = {
            "cpu_stats": {
                "cpu_usage": {"total_usage": 100000000},
                "system_cpu_usage": 500000000
            }
        }
        # cpu_delta = 100,000,000
        # system_delta = 500,000,000
        # online_cpus = 4
        # vcpus = (1/5) * 4 = 0.8
        vcpus = calculate_cpu_vcpus(stats, prev_stats)
        self.assertAlmostEqual(vcpus, 0.8)

        # Division by zero safety
        self.assertEqual(calculate_cpu_vcpus({}, {}), 0.0)

    def test_calculate_ram_gb(self):
        # 1 GB is 1,073,741,824 bytes
        # usage = 1.5 GB, cache = 0.5 GB -> working_set = 1.0 GB
        stats = {
            "memory_stats": {
                "usage": 1610612736,
                "stats": {"cache": 536870912}
            }
        }
        ram = calculate_ram_gb(stats)
        self.assertAlmostEqual(ram, 1.0)

        # Cgroups v2 fallback key: inactive_file
        stats_v2 = {
            "memory_stats": {
                "usage": 1610612736,
                "stats": {"inactive_file": 536870912}
            }
        }
        ram_v2 = calculate_ram_gb(stats_v2)
        self.assertAlmostEqual(ram_v2, 1.0)

    def test_check_swap_active(self):
        # Case 1: Swap enabled in config (MemorySwap > Memory)
        container_mock = MagicMock()
        container_mock.attrs = {
            "HostConfig": {
                "Memory": 536870912,
                "MemorySwap": 1073741824
            }
        }
        active, usage = check_swap_active(container_mock, {})
        self.assertTrue(active)
        self.assertEqual(usage, 0.0)

        # Case 2: Swap active in stats usage (even if config not set or default)
        container_mock_2 = MagicMock()
        container_mock_2.attrs = {
            "HostConfig": {
                "Memory": 536870912,
                "MemorySwap": 536870912
            }
        }
        stats = {
            "memory_stats": {
                "stats": {"swap": 1073741824}
            }
        }
        active_2, usage_2 = check_swap_active(container_mock_2, stats)
        self.assertTrue(active_2)
        self.assertEqual(usage_2, 1.0)

    def test_get_dir_size(self):
        # Write some temporary files and test size calculation
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = os.path.join(tmpdir, "test1.txt")
            file2 = os.path.join(tmpdir, "test2.txt")
            with open(file1, "wb") as f:
                f.write(b"a" * 100)
            with open(file2, "wb") as f:
                f.write(b"b" * 200)
                
            self.assertEqual(get_dir_size(tmpdir), 300)

    @patch("docker.from_env")
    def test_detect_project_name_explicit(self, mock_from_env):
        # If project name is provided, return it
        p_name, c_file = detect_project_name(project_name="my-project")
        self.assertEqual(p_name, "my-project")

    @patch("docker.from_env")
    def test_detect_project_name_from_file(self, mock_from_env):
        with tempfile.NamedTemporaryFile(suffix=".yml", mode="w", delete=False) as tmp:
            yaml.dump({"name": "config-project"}, tmp)
            tmp_name = tmp.name

        try:
            p_name, c_file = detect_project_name(compose_file=tmp_name)
            self.assertEqual(p_name, "config-project")
            self.assertEqual(c_file, os.path.abspath(tmp_name))
        finally:
            os.remove(tmp_name)

if __name__ == "__main__":
    unittest.main()
