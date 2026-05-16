import json
from calculations import simulate_wealth

params = {
    'current_age': 30, 'end_age': 95, 'early_retirement_age': 58, 
    'salary': 60000.0, 'partial_salary': 0.0, 'target_net_income': 3000.0,
    'do_partial_ret': False, 'final_ret_age': 58,
    'inflation': 2.0, 'return_pre': 6.0, 'return_post': 4.0, 'basiszinssatz': 3.20,
    'stock_initial': 50000.0, 'stock_monthly': 500.0, 'etf_switches': 0,
    'priv_initial': 10000.0, 'priv_monthly': 200.0,
    'priv_fee_contrib': 0.50, 'priv_fee_balance': 0.22,
    'current_ep': 10.0,
    'gkv_status': 'KVdR', 
    'kv_rate': 17.5, 'pv_rate': 3.6
}

df = simulate_wealth(params)

df_part = df[(df['Age'] > 58) & (df['Age'] <= 60)]
for index, row in df_part.iterrows():
    print(f"Age: {row['Age']}")
    print(f"  GKV Cost (Real): {row['GKV Cost']:.2f}")
    print(f"  Priv Payout (Real): {row['Priv Payout (Gross)']:.2f}")
    print(f"  Stock Withdrawal (Real): {row['Stock Withdrawal (Gross)']:.2f}")

