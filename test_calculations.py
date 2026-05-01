import unittest
import os
import json
import pandas as pd
from calculations import calc_vorabpauschale, calc_income_tax_2026, simulate_wealth, calculate_flat_savings_equivalent

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
        self.assertAlmostEqual(calc_income_tax_2026(15000), 440.721163, places=5)
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

    def test_default_json_parameters(self):
        """
        Test the simulation with the default parameters from rentenplaner_params_default.json.
        """
        json_path = os.path.join(os.path.dirname(__file__), 'rentenplaner_params_default.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            raw_params = json.load(f)
        
        params = {
            'current_age': raw_params['current_age'],
            'end_age': raw_params['end_age'],
            'early_retirement_age': raw_params['early_retirement_age'],
            'do_partial_ret': raw_params.get('do_partial_retirement', False),
            'final_ret_age': raw_params['early_retirement_age'] + raw_params.get('partial_duration', 0),
            'partial_salary': raw_params['partial_salary'],
            'stock_initial': raw_params['stock_initial'],
            'priv_initial': raw_params['priv_initial'],
            'current_ep': raw_params['current_ep'],
            'inflation': raw_params['inflation'],
            'return_pre': raw_params['return_pre'],
            'return_post': raw_params['return_post'],
            'salary': raw_params['salary'],
            'priv_fee_contrib': raw_params['priv_fee_contrib'],
            'priv_fee_balance': raw_params['priv_fee_balance'],
            'priv_monthly': raw_params['priv_monthly'],
            'kv_rate': raw_params['kv_rate'],
            'pv_rate': raw_params['pv_rate'],
            'gkv_status': raw_params.get('gkv_status_display', 'KVdR'),
            'target_net_income': raw_params['target_net'],
            'stock_monthly': raw_params['stock_monthly'],
            'basiszinssatz': raw_params['basiszinssatz'],
            'etf_switches': raw_params.get('etf_switches', 0)
        }
        
        df = simulate_wealth(params)
        self.assertFalse(df.empty)
        self.assertEqual(len(df), params['end_age'] - params['current_age'] + 1)
        
        df.set_index('Age', inplace=True)
        # At age 63 (during partial retirement from 62 to 64), partial salary should be evaluated.
        # It's an important edge case explicitly testing partial retirement.
        if params['do_partial_ret'] and params['final_ret_age'] > params['early_retirement_age']:
            test_age = params['early_retirement_age'] + 1
            self.assertGreater(df.loc[test_age, 'Partial Salary (Gross)'], 0.0)

    def test_calculate_flat_savings_equivalent(self):
        """
        Test the static calculation of flat savings equivalents.
        """
        params = {
            'current_age': 30,
            'early_retirement_age': 67,
            'inflation': 2.0,
            'return_pre': 6.0,
            'priv_fee_contrib': 0.50,
            'priv_fee_balance': 0.22,
            'stock_monthly': 500,
            'priv_monthly': 200,
        }
        stock_flat, priv_flat = calculate_flat_savings_equivalent(params)
        self.assertGreater(stock_flat, params['stock_monthly'])
        self.assertGreater(priv_flat, params['priv_monthly'])

    def test_voluntary_gkv_edge_case(self):
        """
        Test that a privatier without state pension and high withdrawals pays voluntary GKV.
        """
        params = {
            'current_age': 55,
            'end_age': 70,
            'early_retirement_age': 56,
            'stock_initial': 1000000,
            'priv_initial': 0,
            'current_ep': 10,
            'inflation': 2.0,
            'return_pre': 6.0,
            'return_post': 4.0,
            'salary': 0,
            'partial_salary': 0,
            'priv_fee_contrib': 0,
            'priv_fee_balance': 0,
            'priv_monthly': 0,
            'kv_rate': 14.6,
            'pv_rate': 3.6,
            'gkv_status': 'Freiwillig', 
            'target_net_income': 5000,
            'stock_monthly': 0,
            'basiszinssatz': 3.2
        }
        df = simulate_wealth(params)
        df.set_index('Age', inplace=True)
        
        # Age 56: Privatier Phase
        self.assertGreater(df.loc[56, 'GKV Cost'], 0)
        
        # Age 68: State pension + voluntary GKV
        self.assertGreater(df.loc[68, 'GKV Cost'], 0)

    def test_etf_switches_and_fifo(self):
        """
        Test that ETF switches logic runs correctly (multiple lots exist).
        """
        params = {
            'current_age': 60,
            'end_age': 70,
            'early_retirement_age': 65,
            'stock_initial': 100000,
            'priv_initial': 0,
            'current_ep': 10,
            'inflation': 2.0,
            'return_pre': 6.0,
            'return_post': 4.0,
            'salary': 50000,
            'partial_salary': 0,
            'priv_fee_contrib': 0,
            'priv_fee_balance': 0,
            'priv_monthly': 0,
            'kv_rate': 14.6,
            'pv_rate': 3.6,
            'gkv_status': 'KVdR', 
            'target_net_income': 4000,
            'stock_monthly': 1000,
            'basiszinssatz': 3.2,
            'etf_switches': 2
        }
        df = simulate_wealth(params)
        df.set_index('Age', inplace=True)
        # Should have stock withdrawal during retirement
        self.assertGreater(df.loc[66, 'Stock Withdrawal (Gross)'], 0)

    def test_zero_returns(self):
        """
        Test edge case with 0% returns, 0% inflation.
        """
        params = {
            'current_age': 60,
            'end_age': 65,
            'early_retirement_age': 62,
            'stock_initial': 100000,
            'priv_initial': 50000,
            'current_ep': 10,
            'inflation': 0.0,
            'return_pre': 0.0,
            'return_post': 0.0,
            'salary': 50000,
            'partial_salary': 0,
            'priv_fee_contrib': 0,
            'priv_fee_balance': 0,
            'priv_monthly': 0,
            'kv_rate': 14.6,
            'pv_rate': 3.6,
            'gkv_status': 'KVdR',
            'target_net_income': 3000,
            'stock_monthly': 0,
            'basiszinssatz': 3.2
        }
        df = simulate_wealth(params)
        self.assertEqual(len(df), 6)
        # Real stock balance should decrease without growth
        self.assertTrue(df.iloc[-1]['Real Stock Balance'] <= df.iloc[0]['Real Stock Balance'])

if __name__ == '__main__':
    unittest.main()
