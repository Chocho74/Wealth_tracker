import pandas as pd

def calc_vorabpauschale(value_start, value_end, basiszinssatz, sparerpauschbetrag, contrib=0.0):
    """Calculates Vorabpauschale with 30% Teilfreistellung and applies Sparerpauschbetrag."""
    wertzuwachs = max(0, value_end - value_start - contrib)
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
    stock_lots = [{'basis': stock_basis, 'value': stock_balance, 'etf_id': 0}] if stock_balance > 0 else []
    
    priv_balance = params['priv_initial']
    priv_basis = params['priv_initial']
    priv_lots = [{'basis': priv_basis, 'value': priv_balance}] if priv_balance > 0 else []
    
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
            state_pension_gross = ep * 42.52 * 12 * deflator
            
        # --- MODULE 2: Private Pension ---
        priv_payout_gross = 0
        taxable_gain = 0
        
        fee_contrib_rate = params.get('priv_fee_contrib', 0.50) / 100.0
        fee_balance_rate = params.get('priv_fee_balance', 0.22) / 100.0
        
        if current_year_age < priv_stop_age:
            # Phase A: Accumulation
            contrib = params['priv_monthly'] * 12 * deflator
            net_contrib = contrib * (1 - fee_contrib_rate)
            
            for lot in priv_lots:
                lot['value'] = lot['value'] * (1 + ret) * (1 - fee_balance_rate)
                
            if contrib > 0:
                new_lot_value = net_contrib * (1 + ret) * (1 - fee_balance_rate)
                priv_lots.append({'basis': contrib, 'value': new_lot_value})
                
            priv_balance = sum(lot['value'] for lot in priv_lots)
            priv_basis = sum(lot['basis'] for lot in priv_lots)
            
        elif current_year_age < priv_payout_age:
            # Phase B: Stagnation / Growth
            for lot in priv_lots:
                lot['value'] = lot['value'] * (1 + ret) * (1 - fee_balance_rate)
            priv_balance = sum(lot['value'] for lot in priv_lots)
            priv_basis = sum(lot['basis'] for lot in priv_lots)
            
        elif current_year_age <= priv_payout_end_age:
            # Phase C: Payout
            for lot in priv_lots:
                lot['value'] = lot['value'] * (1 + ret) * (1 - fee_balance_rate)
            priv_balance = sum(lot['value'] for lot in priv_lots)
            priv_basis = sum(lot['basis'] for lot in priv_lots)

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
            
            remaining_to_withdraw = payout
            basis_withdrawn = 0
            
            new_priv_lots = []
            for lot in priv_lots:
                if remaining_to_withdraw <= 0:
                    new_priv_lots.append(lot)
                    continue
                    
                withdraw_from_lot = min(remaining_to_withdraw, lot['value'])
                fraction = withdraw_from_lot / lot['value'] if lot['value'] > 0 else 0
                basis_from_lot = lot['basis'] * fraction
                
                remaining_to_withdraw -= withdraw_from_lot
                basis_withdrawn += basis_from_lot
                
                lot['value'] -= withdraw_from_lot
                lot['basis'] -= basis_from_lot
                
                if lot['value'] > 0.001:
                    new_priv_lots.append(lot)
                    
            priv_lots = new_priv_lots
            priv_balance = sum(lot['value'] for lot in priv_lots)
            priv_basis = sum(lot['basis'] for lot in priv_lots)
            
            gain = payout - basis_withdrawn
            
            # Halbeinkünfteverfahren Taxation (12/62 Rule)
            taxable_gain = gain * (1 - 0.15) * 0.50
            
        else:
            # Phase D: After Private Pension
            priv_balance = 0
            priv_basis = 0
            priv_lots = []
            priv_payout_gross = 0
            taxable_gain = 0
            
        # --- GKV Calculation ---
        gkv_cost = 0
        gkv_rate = (params['kv_rate'] + params['pv_rate']) / 100.0
        kvdr_kv_rate = (params['kv_rate'] / 2.0) / 100.0 # State subsidizes 50% KV
        kvdr_pv_rate = params['pv_rate'] / 100.0         # Full PV
        
        bbg_gkv = 69750 * deflator
        min_gkv_income = 14140 * deflator # Mindestbemessungsgrundlage for freiwillig Versicherte (~1178€/Monat in 2024)
        
        is_privatier = (current_year_age >= early_ret_age) and (current_year_age < state_ret_age)
        current_assessed_income_for_gkv = 0
        base_income_for_gkv = 0
        
        if current_year_age >= state_ret_age:
            if params['gkv_status'] == 'KVdR':
                gkv_cost = state_pension_gross * (kvdr_kv_rate + kvdr_pv_rate)
            else:
                base_income_for_gkv = state_pension_gross + priv_payout_gross
                current_assessed_income_for_gkv = max(base_income_for_gkv, min_gkv_income)
                gkv_cost = min(current_assessed_income_for_gkv, bbg_gkv) * gkv_rate 
        elif is_privatier:
            base_income_for_gkv = priv_payout_gross
            current_assessed_income_for_gkv = max(base_income_for_gkv, min_gkv_income)
            gkv_cost = min(current_assessed_income_for_gkv, bbg_gkv) * gkv_rate
        elif current_year_age >= priv_payout_age:
            if params['gkv_status'] != 'KVdR':
                base_income_for_gkv = user_salary_gross + priv_payout_gross
                current_assessed_income_for_gkv = max(base_income_for_gkv, min_gkv_income)
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
            net_income_so_far = max(0, user_salary_gross + state_pension_gross + priv_payout_gross - salary_tax - state_tax - priv_tax - salary_gkv_deduction - gkv_cost)
            target_net_nominal = (params['target_net_income'] * 12) * deflator
            shortfall = max(0, target_net_nominal - net_income_so_far)
            
        # --- MODULE 1: Stock Market & Depletion ---
        stock_start = stock_balance
        stock_tax_vp = 0
        stock_tax_withdrawal = 0
        stock_withdrawal = 0
        
        # Grow existing lots
        for lot in stock_lots:
            lot['value'] *= (1 + ret)
            
        if current_year_age < early_ret_age:
            # Accumulation phase
            contrib = params['stock_monthly'] * 12 * deflator
            
            etf_switches = params.get('etf_switches', 0)
            num_etfs = etf_switches + 1
            accumulation_years = early_ret_age - age
            if accumulation_years > 0:
                year_index = current_year_age - age - 1
                etf_id = int(year_index / (accumulation_years / num_etfs))
                etf_id = min(etf_id, etf_switches)
            else:
                etf_id = 0

            if contrib > 0:
                stock_lots.append({'basis': contrib, 'value': contrib, 'etf_id': etf_id})
            
            stock_balance_before_vp = sum(lot['value'] for lot in stock_lots)
            vp_tax, sparerpauschbetrag = calc_vorabpauschale(stock_start, stock_balance_before_vp, params['basiszinssatz']/100.0, sparerpauschbetrag, contrib=contrib)
            stock_tax_vp = vp_tax
            
            if stock_balance_before_vp > 0:
                vp_base_total = min(stock_start * (params['basiszinssatz']/100.0) * 0.7, max(0, stock_balance_before_vp - stock_start - contrib))
                for lot in stock_lots:
                    fraction = lot['value'] / stock_balance_before_vp
                    lot['basis'] += vp_base_total * fraction
                    lot['value'] -= vp_tax * fraction
            stock_balance = sum(lot['value'] for lot in stock_lots)
        else:
            # Retirement / Partial Retirement phase
            stock_balance_before_vp = sum(lot['value'] for lot in stock_lots)
            vp_tax, sparerpauschbetrag = calc_vorabpauschale(stock_start, stock_balance_before_vp, params['basiszinssatz']/100.0, sparerpauschbetrag)
            stock_tax_vp = vp_tax
            
            if stock_balance_before_vp > 0:
                vp_base_total = min(stock_start * (params['basiszinssatz']/100.0) * 0.7, max(0, stock_balance_before_vp - stock_start))
                for lot in stock_lots:
                    fraction = lot['value'] / stock_balance_before_vp
                    lot['basis'] += vp_base_total * fraction
                    lot['value'] -= vp_tax * fraction
            stock_balance = sum(lot['value'] for lot in stock_lots)
            
            if shortfall > 0:
                is_voluntary = is_privatier or (current_year_age >= state_ret_age and params['gkv_status'] != 'KVdR')
                
                # Build ordered_lots based on ETF strategy (youngest ETF first)
                ordered_lots = []
                for current_etf in range(params.get('etf_switches', 0), -1, -1):
                    ordered_lots.extend([lot for lot in stock_lots if lot.get('etf_id', 0) == current_etf])
                
                # Check if withdrawing everything is still not enough
                temp_gross = stock_balance
                temp_gain = 0
                for lot in ordered_lots:
                    lot_gain = max(0, lot['value'] - lot['basis']) * 0.70
                    temp_gain += lot_gain
                used_freibetrag_temp = min(temp_gain, sparerpauschbetrag)
                taxable_temp = temp_gain - used_freibetrag_temp
                temp_tax = taxable_temp * 0.26375
                temp_gkv = 0
                if is_voluntary:
                    total_income_temp = base_income_for_gkv + temp_gain
                    new_assessed = max(total_income_temp, min_gkv_income)
                    temp_gkv = max(0, min(new_assessed, bbg_gkv) * gkv_rate - gkv_cost)
                max_net = temp_gross - temp_tax - temp_gkv
                
                best_gross = stock_balance
                if max_net > shortfall:
                    # Binary search
                    low = shortfall
                    high = min(stock_balance, shortfall * 2.0)
                    for _ in range(30):
                        mid = (low + high) / 2.0
                        temp_gross = mid
                        temp_gain = 0
                        for lot in ordered_lots:
                            if temp_gross <= 0: break
                            withdraw_from_lot = min(temp_gross, lot['value'])
                            fraction = withdraw_from_lot / lot['value']
                            basis_withdrawn = lot['basis'] * fraction
                            temp_gain += max(0, withdraw_from_lot - basis_withdrawn) * 0.70
                            temp_gross -= withdraw_from_lot
                            
                        used_freibetrag_temp = min(temp_gain, sparerpauschbetrag)
                        taxable_temp = temp_gain - used_freibetrag_temp
                        temp_tax = taxable_temp * 0.26375
                        
                        temp_gkv = 0
                        if is_voluntary:
                            total_income_temp = base_income_for_gkv + temp_gain
                            new_assessed = max(total_income_temp, min_gkv_income)
                            temp_gkv = max(0, min(new_assessed, bbg_gkv) * gkv_rate - gkv_cost)
                            
                        net_temp = mid - temp_tax - temp_gkv
                        
                        if net_temp >= shortfall:
                            high = mid
                        else:
                            low = mid
                    best_gross = high
                
                stock_withdrawal = best_gross
                gain_portion = 0
                remaining_to_withdraw = best_gross
                
                for lot in ordered_lots:
                    if remaining_to_withdraw <= 0:
                        break
                        
                    withdraw_from_lot = min(remaining_to_withdraw, lot['value'])
                    fraction = withdraw_from_lot / lot['value']
                    basis_withdrawn = lot['basis'] * fraction
                    gain_portion += max(0, withdraw_from_lot - basis_withdrawn) * 0.70
                    
                    remaining_to_withdraw -= withdraw_from_lot
                    
                    lot['value'] -= withdraw_from_lot
                    lot['basis'] -= basis_withdrawn
                    
                stock_lots = [lot for lot in stock_lots if lot['value'] > 0.001]
                stock_balance = sum(lot['value'] for lot in stock_lots)
                
                used_freibetrag = min(gain_portion, sparerpauschbetrag)
                stock_tax_withdrawal = max(0, gain_portion - used_freibetrag) * 0.26375
                sparerpauschbetrag -= used_freibetrag
                
                if is_voluntary:
                    total_income = base_income_for_gkv + gain_portion
                    new_assessed = max(total_income, min_gkv_income)
                    additional_gkv = max(0, min(new_assessed, bbg_gkv) * gkv_rate - gkv_cost)
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

