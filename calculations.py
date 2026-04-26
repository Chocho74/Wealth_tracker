import pandas as pd

def calc_vorabpauschale(value_start, value_end, basiszinssatz, sparerpauschbetrag):
    """Calculates Vorabpauschale with 30% Teilfreistellung and applies Sparerpauschbetrag."""
    wertzuwachs = max(0, value_end - value_start)
    basisertrag = value_start * basiszinssatz * 0.7
    vorabpauschale = min(basisertrag, wertzuwachs)
    
    # 30% Teilfreistellung for Aktienfonds
    taxable_amount = vorabpauschale * 0.70
    
    used_freibetrag = min(taxable_amount, sparerpauschbetrag)
    taxable_amount -= used_freibetrag
    sparerpauschbetrag_remaining = sparerpauschbetrag - used_freibetrag
    
    # Abgeltungsteuer + Soli = 26.375%
    tax = taxable_amount * 0.26375
    return tax, sparerpauschbetrag_remaining

def calc_income_tax_2024(zvE):
    """Calculates the German income tax (ESt) based on the 2024 formula (§ 32a EStG)."""
    x = int(zvE)
    if x <= 11784:
        return 0.0
    elif x <= 17005:
        y = (x - 11784) / 10000.0
        return (954.80 * y + 1400.0) * y
    elif x <= 66760:
        z = (x - 17005) / 10000.0
        return (181.19 * z + 2397.0) * z + 991.21
    elif x <= 277825:
        return 0.42 * x - 10636.31
    else:
        return 0.45 * x - 18971.06

def simulate_wealth(params):
    records = []
    
    age = params['current_age']
    end_age = params['end_age']
    early_ret_age = params.get('early_retirement_age', 67)
    
    # Initial Balances
    stock_balance = params['stock_initial']
    stock_basis = params['stock_initial']
    
    priv_balance = params['priv_initial']
    priv_basis = params['priv_initial']
    
    ep = params['current_ep']
    
    # Milestones
    priv_stop_age = 50
    priv_payout_age = 62
    priv_payout_end_age = 85
    state_ret_age = 67
    
    priv_annuity = 0
    inflation_rate = params['inflation'] / 100.0
    
    # Initial State (Row 0)
    records.append({
        'Age': age,
        'Real Stock Balance': stock_balance,
        'Real Priv Pension Balance': priv_balance,
        'State Pension (Gross)': 0.0,
        'Priv Payout (Gross)': 0.0,
        'Stock Withdrawal (Gross)': 0.0,
        'Partial Salary (Gross)': 0.0,
        'Total Taxes & GKV': 0.0,
        'State Tax': 0.0,
        'Priv Tax': 0.0,
        'Salary Tax': 0.0,
        'Stock Tax': 0.0,
        'Vorabpauschale': 0.0,
        'GKV Cost': 0.0,
        'Rentenpunkte': ep
    })
    
    for current_year_age in range(age + 1, end_age + 1):
        # Determine current return based on phase
        ret = params['return_pre']/100.0 if current_year_age < early_ret_age else params['return_post']/100.0
        sparerpauschbetrag = 1000.0
        
        # Inflation Deflator for the current year
        deflator = (1 + inflation_rate) ** (current_year_age - age)
        
        # --- MODULE 3: State Pension & Salary ---
        state_pension_gross = 0
        user_salary_gross = 0
        if current_year_age < early_ret_age:
            if current_year_age < priv_payout_age:
                user_salary_gross = params['salary'] * deflator
            else:
                user_salary_gross = params['partial_salary'] * deflator
            ep += min(user_salary_gross / deflator, 101400) / 51944.0
            
        if current_year_age >= state_ret_age:
            state_pension_gross = ep * 40.79 * 12 * deflator
            
        # --- MODULE 2: Private Pension ---
        priv_payout_gross = 0
        taxable_gain = 0
        
        fee_contrib_rate = params.get('priv_fee_contrib', 0.50) / 100.0
        fee_balance_rate = params.get('priv_fee_balance', 0.22) / 100.0
        
        if current_year_age < priv_stop_age:
            # Phase A: Accumulation
            contrib = params['priv_monthly'] * 12 * deflator
            priv_basis += contrib
            net_contrib = contrib * (1 - fee_contrib_rate)
            priv_balance = (priv_balance + net_contrib) * (1 + ret)
            priv_balance *= (1 - fee_balance_rate)
            
        elif current_year_age < priv_payout_age:
            # Phase B: Stagnation / Growth
            priv_balance *= (1 + ret)
            priv_balance *= (1 - fee_balance_rate)
            
        elif current_year_age <= priv_payout_end_age:
            # Phase C: Payout
            net_ret = ret - fee_balance_rate
            periods_remaining = priv_payout_end_age - current_year_age + 1
            
            if net_ret != 0:
                priv_annuity = (net_ret * priv_balance) / (1 - (1+net_ret)**-periods_remaining)
            else:
                priv_annuity = priv_balance / periods_remaining
            
            # Ensure the last year clears the balance completely to avoid floating point leftovers
            if current_year_age == priv_payout_end_age:
                payout = priv_balance
            else:
                payout = min(priv_annuity, priv_balance)
                
            priv_payout_gross = payout
            
            withdrawal_fraction = payout / priv_balance if priv_balance > 0 else 0
            basis_withdrawn = priv_basis * withdrawal_fraction
            gain = payout - basis_withdrawn
            
            priv_basis -= basis_withdrawn
            priv_balance -= payout
            priv_balance *= (1 + ret)
            priv_balance *= (1 - fee_balance_rate)
            
            # Halbeinkünfteverfahren Taxation (12/62 Rule)
            taxable_gain = gain * (1 - 0.15) * 0.50
            
        else:
            # Phase D: After Private Pension
            priv_balance = 0
            priv_basis = 0
            priv_payout_gross = 0
            taxable_gain = 0
            
        # --- GKV Calculation ---
        gkv_cost = 0
        gkv_rate = (params['kv_rate'] + params['pv_rate']) / 100.0
        kvdr_kv_rate = (params['kv_rate'] / 2.0) / 100.0 # State subsidizes 50% KV
        kvdr_pv_rate = params['pv_rate'] / 100.0         # Full PV
        
        bbg_gkv = 69750 * deflator
        is_privatier = (current_year_age >= early_ret_age) and (current_year_age < state_ret_age)
        current_assessed_income_for_gkv = 0
        
        if current_year_age >= state_ret_age:
            if params['gkv_status'] == 'KVdR':
                gkv_cost = state_pension_gross * (kvdr_kv_rate + kvdr_pv_rate)
            else:
                current_assessed_income_for_gkv = state_pension_gross + priv_payout_gross
                gkv_cost = min(current_assessed_income_for_gkv, bbg_gkv) * gkv_rate 
        elif is_privatier:
            current_assessed_income_for_gkv = priv_payout_gross
            gkv_cost = min(current_assessed_income_for_gkv, bbg_gkv) * gkv_rate
        elif current_year_age >= priv_payout_age:
            if params['gkv_status'] != 'KVdR':
                current_assessed_income_for_gkv = user_salary_gross + priv_payout_gross
                gkv_cost = min(current_assessed_income_for_gkv, bbg_gkv) * gkv_rate

        # Estimate GKV on salary for tax deduction purposes
        salary_gkv_deduction = user_salary_gross * 0.10 if user_salary_gross > 0 else 0
        
        nominal_taxable_income_total = max(0, user_salary_gross + state_pension_gross + taxable_gain - gkv_cost - salary_gkv_deduction)
        real_taxable_income_total = nominal_taxable_income_total / deflator
        real_tax_total = calc_income_tax_2024(real_taxable_income_total)
        total_nominal_income_tax = real_tax_total * deflator

        # Distribute tax proportionally
        total_taxable_before_deductions = user_salary_gross + state_pension_gross + taxable_gain
        if total_taxable_before_deductions > 0:
            salary_tax = total_nominal_income_tax * (user_salary_gross / total_taxable_before_deductions)
            state_tax = total_nominal_income_tax * (state_pension_gross / total_taxable_before_deductions)
            priv_tax = total_nominal_income_tax * (taxable_gain / total_taxable_before_deductions)
        else:
            salary_tax = 0
            state_tax = 0
            priv_tax = 0
            
        target_phase_started = current_year_age >= min(early_ret_age, priv_payout_age)
        
        net_income_so_far = 0
        shortfall = 0
        if target_phase_started:
            net_salary = max(0, user_salary_gross - salary_tax - salary_gkv_deduction)
            
            net_state_pension = 0
            if state_pension_gross > 0:
                if params['gkv_status'] == 'KVdR':
                    net_state_pension = state_pension_gross - state_tax - (state_pension_gross * (kvdr_kv_rate + kvdr_pv_rate))
                else:
                    gkv_on_state = min(state_pension_gross, bbg_gkv) * gkv_rate
                    net_state_pension = state_pension_gross - state_tax - gkv_on_state
                    
            net_priv_pension = 0
            if priv_payout_gross > 0:
                if params['gkv_status'] == 'KVdR' and not is_privatier:
                    net_priv_pension = priv_payout_gross - priv_tax
                else:
                    gkv_on_priv = min(priv_payout_gross, max(0, bbg_gkv - state_pension_gross - user_salary_gross)) * gkv_rate
                    net_priv_pension = priv_payout_gross - priv_tax - gkv_on_priv
            
            net_income_so_far = net_salary + net_state_pension + net_priv_pension
            target_net_nominal = (params['target_net_income'] * 12) * deflator
            shortfall = max(0, target_net_nominal - net_income_so_far)
            
        # --- MODULE 1: Stock Market & Depletion ---
        stock_start = stock_balance
        stock_tax_vp = 0
        stock_tax_withdrawal = 0
        stock_withdrawal = 0
        
        if current_year_age < early_ret_age:
            # Accumulation phase
            contrib = params['stock_monthly'] * 12 * deflator
            stock_basis += contrib
            stock_balance = (stock_balance + contrib) * (1 + ret)
            
            vp_tax, sparerpauschbetrag = calc_vorabpauschale(stock_start, stock_balance, params['basiszinssatz']/100.0, sparerpauschbetrag)
            stock_tax_vp = vp_tax
            stock_balance -= vp_tax
        else:
            # Retirement / Partial Retirement phase
            stock_balance *= (1 + ret)
            
            vp_tax, sparerpauschbetrag = calc_vorabpauschale(stock_start, stock_balance, params['basiszinssatz']/100.0, sparerpauschbetrag)
            stock_tax_vp = vp_tax
            stock_balance -= vp_tax
            
            if shortfall > 0:
                effective_tax_rate = 0.50 * 0.26375
                is_voluntary = is_privatier or params['gkv_status'] != 'KVdR'
                
                if is_voluntary:
                    effective_tax_rate += 0.50 * gkv_rate
                    
                gross_withdrawal = shortfall / (1 - effective_tax_rate)
                stock_withdrawal = min(gross_withdrawal, stock_balance)
                stock_balance -= stock_withdrawal
                
                gain_portion = stock_withdrawal * 0.50
                used_freibetrag = min(gain_portion, sparerpauschbetrag)
                stock_tax_withdrawal = max(0, gain_portion - used_freibetrag) * 0.26375
                sparerpauschbetrag -= used_freibetrag
                
                if is_voluntary:
                    new_assessed = current_assessed_income_for_gkv + gain_portion
                    additional_gkv = max(0, min(new_assessed, bbg_gkv) - min(current_assessed_income_for_gkv, bbg_gkv)) * gkv_rate
                    gkv_cost += additional_gkv
            
        total_taxes = salary_tax + state_tax + priv_tax + stock_tax_withdrawal + stock_tax_vp + gkv_cost
            
        records.append({
            'Age': current_year_age,
            'Real Stock Balance': max(0, stock_balance) / deflator,
            'Real Priv Pension Balance': max(0, priv_balance) / deflator,
            'State Pension (Gross)': state_pension_gross / deflator,
            'Priv Payout (Gross)': priv_payout_gross / deflator,
            'Stock Withdrawal (Gross)': stock_withdrawal / deflator,
            'Partial Salary (Gross)': user_salary_gross / deflator if (current_year_age >= priv_payout_age and current_year_age < early_ret_age) else 0.0,
            'Total Taxes & GKV': total_taxes / deflator,
            'State Tax': state_tax / deflator,
            'Priv Tax': priv_tax / deflator,
            'Salary Tax': salary_tax / deflator,
            'Stock Tax': stock_tax_withdrawal / deflator,
            'Vorabpauschale': stock_tax_vp / deflator,
            'GKV Cost': gkv_cost / deflator,
            'Rentenpunkte': ep
        })
        
    return pd.DataFrame(records)

def calculate_flat_savings_equivalent(params):
    """
    Calculates the equivalent flat monthly savings rate that yields the same nominal 
    contribution future value as the inflation-adjusted savings, avoiding the need 
    to increase monthly deposits each year.
    """
    age = params['current_age']
    early_ret_age = params.get('early_retirement_age', 67)
    priv_stop_age = 50
    
    inflation_rate = params['inflation'] / 100.0
    ret_pre = params['return_pre'] / 100.0
    
    fee_contrib_rate = params.get('priv_fee_contrib', 0.50) / 100.0
    fee_balance_rate = params.get('priv_fee_balance', 0.22) / 100.0
    
    stock_monthly = params['stock_monthly']
    priv_monthly = params['priv_monthly']
    
    # 1. Stock equivalent
    stock_fv_adj = 0.0
    stock_fv_flat = 0.0
    for current_year_age in range(age + 1, early_ret_age + 1):
        deflator = (1 + inflation_rate) ** (current_year_age - age)
        stock_fv_adj = (stock_fv_adj + stock_monthly * 12 * deflator) * (1 + ret_pre)
        stock_fv_flat = (stock_fv_flat + 1.0 * 12) * (1 + ret_pre)
        
    stock_flat = (stock_fv_adj / stock_fv_flat) if stock_fv_flat > 0 else stock_monthly
    
    # 2. Private Pension equivalent
    priv_fv_adj = 0.0
    priv_fv_flat = 0.0
    for current_year_age in range(age + 1, priv_stop_age + 1):
        deflator = (1 + inflation_rate) ** (current_year_age - age)
        net_contrib_adj = (priv_monthly * 12 * deflator) * (1 - fee_contrib_rate)
        priv_fv_adj = (priv_fv_adj + net_contrib_adj) * (1 + ret_pre) * (1 - fee_balance_rate)
        
        net_contrib_flat = (1.0 * 12) * (1 - fee_contrib_rate)
        priv_fv_flat = (priv_fv_flat + net_contrib_flat) * (1 + ret_pre) * (1 - fee_balance_rate)
        
    priv_flat = (priv_fv_adj / priv_fv_flat) if priv_fv_flat > 0 else priv_monthly
    
    return stock_flat, priv_flat

