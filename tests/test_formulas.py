import unittest
from vdecent_size.formulas import (
    calculate_base_vru,
    calculate_storage_penalty,
    resolve_tier_and_vru,
    TIER_S, TIER_M, TIER_L, TIER_XL
)

class TestFormulas(unittest.TestCase):
    def test_base_vru(self):
        # Baseline S: CPU=0.2, RAM=0.5 GB -> VRU should be exactly 1.0
        self.assertAlmostEqual(calculate_base_vru(0.2, 0.5), 1.0)
        # Double baseline: CPU=0.4, RAM=1.0 GB -> VRU should be 2.0
        self.assertAlmostEqual(calculate_base_vru(0.4, 1.0), 2.0)
        # S-tier bounds test
        self.assertAlmostEqual(calculate_base_vru(0.1, 0.25), 0.5)

    def test_storage_penalty(self):
        # Under ceiling -> penalty is 0
        self.assertEqual(calculate_storage_penalty(3.0, 5.0), 0.0)
        self.assertEqual(calculate_storage_penalty(5.0, 5.0), 0.0)
        # Over ceiling -> linear penalty: (actual - ceiling) / 25
        self.assertAlmostEqual(calculate_storage_penalty(30.0, 5.0), 1.0)
        self.assertAlmostEqual(calculate_storage_penalty(15.0, 10.0), 0.2)

    def test_resolve_tier_and_vru(self):
        # Case 1: Pure S tier, no storage penalty
        tier, vru, penalty = resolve_tier_and_vru(0.2, 0.5, 3.0)
        self.assertEqual(tier, TIER_S)
        self.assertAlmostEqual(vru, 1.0)
        self.assertEqual(penalty, 0.0)

        # Case 2: CPU/RAM fits S but storage pushes it to M
        # Base VRU = 1.1. Storage = 30 GB.
        # VRU_S = 1.1 + (30-5)/25 = 2.1 (> 1.2, so not S)
        # VRU_M = 1.1 + (30-10)/25 = 1.9 (<= 2.4, so M)
        tier, vru, penalty = resolve_tier_and_vru(0.22, 0.55, 30.0)
        self.assertEqual(tier, TIER_M)
        self.assertAlmostEqual(vru, 1.9)
        self.assertAlmostEqual(penalty, 0.8)

        # Case 3: CPU/RAM is M tier from start, storage is low
        tier, vru, penalty = resolve_tier_and_vru(0.4, 1.0, 4.0)
        self.assertEqual(tier, TIER_M)
        self.assertAlmostEqual(vru, 2.0)
        self.assertEqual(penalty, 0.0)

        # Case 4: CPU/RAM is L, storage is very high
        # Base VRU = (0.3 * (0.8/0.2)) + (0.7 * (2.0/0.5)) = 1.2 + 2.8 = 4.0 (Tier L)
        # Storage = 70 GB.
        # VRU_L = 4.0 + (70 - 20)/25 = 6.0 (> 4.8, so XL)
        # VRU_XL = 4.0 + (70 - 40)/25 = 5.2
        tier, vru, penalty = resolve_tier_and_vru(0.8, 2.0, 70.0)
        self.assertEqual(tier, TIER_XL)
        self.assertAlmostEqual(vru, 5.2)
        self.assertAlmostEqual(penalty, 1.2)

if __name__ == "__main__":
    unittest.main()
