import unittest
import os
import pandas as pd
from calculations import calc_vorabpauschale, calc_income_tax_2026, simulate_wealth

class TestCalculations(unittest.TestCase):

    def test_calc_vorabpauschale(self):
        tax, remaining_freibetrag = calc_vorabpauschale(10000, 11000, 0.032, 1000)
        self.assertAlmostEqual(tax, 0.0)
        self.assertAlmostEqual(remaining_freibetrag, 843.2)

        tax, remaining_freibetrag = calc_vorabpauschale(10000, 10100, 0.032, 0)
        self.assertAlmostEqual(tax, 18.4625)
        self.assertAlmostEqual(remaining_freibetrag, 0.0)

    def test_calc_income_tax_2026(self):
        self.assertAlmostEqual(calc_income_tax_2026(10000), 0.0)
        self.assertAlmostEqual(calc_income_tax_2026(15000), 548.991679, places=5)
        self.assertAlmostEqual(calc_income_tax_2026(50000), 10872.6727, places=3)
        self.assertAlmostEqual(calc_income_tax_2026(100000), 31363.69, places=2)
        self.assertAlmostEqual(calc_income_tax_2026(300000), 116028.94, places=2)

    def test_simulate_wealth_regression(self):
        """
        Regression test for simulate_wealth. 
        It runs the simulation with a fixed set of parameters and saves the output to a CSV.
        If the CSV already exists, it compares the current output against the saved CSV 
        to ensure no unintentional changes have been made to the core logic.
        """
        params = {
            'current_age': 30,
            'end_age': 90,
            'stock_initial': 10000,
            'priv_initial': 5000,
            'current_ep': 10,
            'inflation': 2.0,
            'return_pre': 6.0,
            'return_post': 4.0,
            'salary': 60000,
            'partial_salary': 30000,
            'priv_fee_contrib': 0.50,
            'priv_fee_balance': 0.22,
            'priv_monthly': 200,
            'kv_rate': 14.6,
            'pv_rate': 3.6,
            'gkv_status': 'KVdR',
            'target_net_income': 3000,
            'stock_monthly': 500,
            'basiszinssatz': 3.2
        }
        df = simulate_wealth(params)
        
        # Verify the structure and length
        self.assertEqual(len(df), 61)  # age 30 to 90
        
        snapshot_file = os.path.join(os.path.dirname(__file__), 'simulate_wealth_snapshot.csv')
        
        if not os.path.exists(snapshot_file):
            # First run: save the current correct state
            df.to_csv(snapshot_file, index=False)
            print(f"Snapshot created at {snapshot_file}. Please commit this file to version control.")
        else:
            # Subsequent runs: load the snapshot and compare
            expected_df = pd.read_csv(snapshot_file)
            pd.testing.assert_frame_equal(df, expected_df, check_dtype=False, rtol=1e-5, atol=1e-5)

    def test_simulate_wealth_early_retirement(self):
        """
        Regression test for simulate_wealth with early retirement at 55.
        """
        params = {
            'current_age': 30,
            'end_age': 90,
            'early_retirement_age': 55,
            'stock_initial': 10000,
            'priv_initial': 5000,
            'current_ep': 10,
            'inflation': 2.0,
            'return_pre': 6.0,
            'return_post': 4.0,
            'salary': 60000,
            'partial_salary': 30000,
            'priv_fee_contrib': 0.50,
            'priv_fee_balance': 0.22,
            'priv_monthly': 200,
            'kv_rate': 14.6,
            'pv_rate': 3.6,
            'gkv_status': 'KVdR',
            'target_net_income': 3000,
            'stock_monthly': 500,
            'basiszinssatz': 3.2
        }
        df = simulate_wealth(params)
        
        self.assertEqual(len(df), 61)  # age 30 to 90
        
        snapshot_file = os.path.join(os.path.dirname(__file__), 'simulate_wealth_early_ret_snapshot.csv')
        
        if not os.path.exists(snapshot_file):
            df.to_csv(snapshot_file, index=False)
            print(f"Early Retirement snapshot created at {snapshot_file}.")
        else:
            expected_df = pd.read_csv(snapshot_file)
            pd.testing.assert_frame_equal(df, expected_df, check_dtype=False, rtol=1e-5, atol=1e-5)

    def test_private_pension_phases(self):
        """
        Explicitly verify that the private pension obeys its fixed milestones:
        - Payout: 62 <= age <= 85
        - Post-Payout: age > 85 (Balance and Payout must be exactly 0)
        """
        params = {
            'current_age': 40,
            'end_age': 90,
            'early_retirement_age': 67,
            'stock_initial': 10000,
            'priv_initial': 5000,
            'current_ep': 10,
            'inflation': 2.0,
            'return_pre': 6.0,
            'return_post': 4.0,
            'salary': 60000,
            'partial_salary': 30000,
            'priv_fee_contrib': 0.50,
            'priv_fee_balance': 0.22,
            'priv_monthly': 200,
            'kv_rate': 14.6,
            'pv_rate': 3.6,
            'gkv_status': 'KVdR',
            'target_net_income': 3000,
            'stock_monthly': 500,
            'basiszinssatz': 3.2
        }
        df = simulate_wealth(params)
        df.set_index('Age', inplace=True)
        
        # Age 62 to 85 should have payout > 0
        for age in range(62, 86):
            self.assertGreater(df.loc[age, 'Priv Payout (Gross)'], 0, f"Age {age} should have a private pension payout.")
        
        # Age 86+ should have 0 balance and 0 payout
        for age in range(86, 91):
            self.assertAlmostEqual(df.loc[age, 'Real Priv Pension Balance'], 0.0, msg=f"Age {age} private pension balance should be 0.")
            self.assertAlmostEqual(df.loc[age, 'Priv Payout (Gross)'], 0.0, msg=f"Age {age} private pension payout should be 0.")

if __name__ == '__main__':
    unittest.main()
