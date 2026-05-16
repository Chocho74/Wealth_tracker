import json
from calculations import simulate_wealth

params = {
    'current_age': 30, 'end_age': 95, 'early_retirement_age': 57, 
    'salary': 60000.0, 'partial_salary': 30000.0, 'target_net_income': 3000.0,
    'do_partial_ret': True, 'final_ret_age': 59,
    'inflation': 2.0, 'return_pre': 6.0, 'return_post': 4.0, 'basiszinssatz': 3.20,
    'stock_initial': 50000.0, 'stock_monthly': 500.0, 'etf_switches': 0,
    'priv_initial': 10000.0, 'priv_monthly': 200.0,
    'priv_fee_contrib': 0.50, 'priv_fee_balance': 0.22,
    'current_ep': 10.0,
    'gkv_status': 'KVdR', 
    'kv_rate': 17.5, 'pv_rate': 3.6
}

df = simulate_wealth(params)

df_part = df[(df['Age'] > 57) & (df['Age'] <= 59)]
for index, row in df_part.iterrows():
    payout = row['State Pension (Gross)'] + row['Priv Payout (Gross)'] + row['Partial Salary (Gross)'] + row['Stock Withdrawal (Gross)']
    taxes = row['Total Taxes & GKV']
    net = payout - taxes
    print(f"Age {row['Age']}: Payout = {payout:.2f}, Taxes = {taxes:.2f}, Net = {net:.2f}, Target = {params['target_net_income']*12:.2f}, Diff = {net - params['target_net_income']*12:.2f}, VP = {row['Vorabpauschale']:.2f}")
