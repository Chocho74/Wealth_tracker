import pandas as pd
from typing import Dict, Any, List, Tuple

def calc_vorabpauschale(value_start: float, value_end: float, basiszinssatz: float, sparerpauschbetrag: float, contrib: float = 0.0) -> Tuple[float, float]:
    """
    Calculates Vorabpauschale with 30% Teilfreistellung and applies Sparerpauschbetrag.
    
    Args:
        value_start: Asset value at the beginning of the year.
        value_end: Asset value at the end of the year.
        basiszinssatz: The base interest rate (e.g., 0.032 for 3.2%).
        sparerpauschbetrag: The remaining tax-free allowance.
        contrib: Contributions made during the year.
        
    Returns:
        A tuple containing the calculated tax and the remaining Sparerpauschbetrag.
    """
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

def calc_income_tax_2026(zvE: float) -> float:
    """
    Calculates the German income tax (ESt) based on the estimated 2026 formula (§ 32a EStG).
    (Using proposed Grundfreibetrag of €12,336).
    
    Args:
        zvE: The taxable income (zu versteuerndes Einkommen).
        
    Returns:
        The calculated income tax.
    """
    x = int(zvE)
    if x <= 12336:
        return 0.0
    elif x <= 17005:
        y = (x - 12336) / 10000.0
        return (954.80 * y + 1400.0) * y
    elif x <= 66760:
        z = (x - 17005) / 10000.0
        return (181.19 * z + 2397.0) * z + 991.21
    elif x <= 277825:
        return 0.42 * x - 10636.31
    else:
        return 0.45 * x - 18971.06


class WealthSimulation:
    """
    Encapsulates the state and logic for simulating wealth, taxes, and retirement over time.
    """
    def __init__(self, params: Dict[str, Any]):
        self.params = params
        self.records: List[Dict[str, Any]] = []
        
        self.age = params['current_age']
        self.end_age = params['end_age']
        self.early_ret_age = params.get('early_retirement_age', 67)
        self.do_partial_ret = params.get('do_partial_ret', False)
        self.final_ret_age = params.get('final_ret_age', self.early_ret_age)
        self.partial_salary = params.get('partial_salary', 0.0)
        self.state_ret_age = 67
        
        self.stock_balance = params['stock_initial']
        self.stock_basis = params['stock_initial']
        self.stock_lots: List[Dict[str, Any]] = [{'basis': self.stock_basis, 'value': self.stock_balance, 'etf_id': 0}] if self.stock_balance > 0 else []
        
        self.priv_balance = params['priv_initial']
        self.priv_basis = params['priv_initial']
        self.priv_lots: List[Dict[str, Any]] = [{'basis': self.priv_basis, 'value': self.priv_balance}] if self.priv_balance > 0 else []
        
        self.ep = params['current_ep']
        
        self.priv_stop_age = 50
        self.priv_payout_age = 62
        self.priv_payout_end_age = 85
        
        self.inflation_rate = params['inflation'] / 100.0
        
        # State variables updated per year
        self.current_year_age = self.age
        self.deflator = 1.0
        self.ret = 0.0
        self.sparerpauschbetrag = 1000.0

    def run(self) -> pd.DataFrame:
        """Executes the simulation year by year."""
        self._record_initial_state()
        for self.current_year_age in range(self.age + 1, self.end_age + 1):
            self._simulate_year()
        return pd.DataFrame(self.records)

    def _record_initial_state(self):
        """Records the initial snapshot at the start age."""
        self.records.append({
            'Age': self.age,
            'Real Stock Balance': self.stock_balance,
            'Real Priv Pension Balance': self.priv_balance,
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
            'Rentenpunkte': self.ep
        })

    def _simulate_year(self):
        """Simulates a single year, updating all state variables."""
        self.ret = self.params['return_pre']/100.0 if self.current_year_age < self.early_ret_age else self.params['return_post']/100.0
        self.sparerpauschbetrag = 1000.0
        self.deflator = (1 + self.inflation_rate) ** (self.current_year_age - self.age)
        
        user_salary_gross, state_pension_gross = self._calc_state_pension_and_salary()
        priv_payout_gross, taxable_gain = self._calc_private_pension()
        
        gkv_cost, base_income_for_gkv, min_gkv_income, is_privatier = self._calc_gkv(
            user_salary_gross, state_pension_gross, priv_payout_gross
        )
        
        salary_tax, state_tax, priv_tax, salary_gkv_deduction = self._calc_income_taxes(
            user_salary_gross, state_pension_gross, taxable_gain, gkv_cost
        )
        
        shortfall = self._calc_shortfall(
            user_salary_gross, state_pension_gross, priv_payout_gross,
            salary_tax, state_tax, priv_tax, salary_gkv_deduction, gkv_cost
        )
        
        stock_withdrawal, stock_tax_vp, stock_tax_withdrawal, additional_gkv = self._calc_stock_market(
            shortfall, is_privatier, base_income_for_gkv, min_gkv_income, gkv_cost
        )
        
        gkv_cost += additional_gkv
        total_taxes = salary_tax + state_tax + priv_tax + stock_tax_withdrawal + stock_tax_vp + gkv_cost
        
        self._record_year(
            state_pension_gross, priv_payout_gross, stock_withdrawal, user_salary_gross,
            total_taxes, state_tax, priv_tax, salary_tax, stock_tax_withdrawal, stock_tax_vp, gkv_cost
        )

    def _calc_state_pension_and_salary(self) -> Tuple[float, float]:
        """Calculates state pension and gross salary, updating Entgeltpunkte."""
        state_pension_gross = 0.0
        user_salary_gross = 0.0
        
        if self.current_year_age < self.early_ret_age:
            user_salary_gross = self.params['salary'] * self.deflator
            self.ep += min(user_salary_gross / self.deflator, 101400) / 51944.0
        elif self.do_partial_ret and self.current_year_age >= self.early_ret_age and self.current_year_age < self.final_ret_age:
            user_salary_gross = self.partial_salary * self.deflator
            self.ep += min(user_salary_gross / self.deflator, 101400) / 51944.0

        if self.current_year_age >= self.state_ret_age:
            state_pension_gross = self.ep * 42.52 * 12 * self.deflator
            
        return user_salary_gross, state_pension_gross

    def _calc_private_pension(self) -> Tuple[float, float]:
        """Calculates private pension growth, payout, and taxable gain."""
        priv_payout_gross = 0.0
        taxable_gain = 0.0
        
        fee_contrib_rate = self.params.get('priv_fee_contrib', 0.50) / 100.0
        fee_balance_rate = self.params.get('priv_fee_balance', 0.22) / 100.0
        
        if self.current_year_age < self.priv_stop_age:
            contrib = self.params['priv_monthly'] * 12 * self.deflator
            net_contrib = contrib * (1 - fee_contrib_rate)
            
            for lot in self.priv_lots:
                lot['value'] = lot['value'] * (1 + self.ret) * (1 - fee_balance_rate)
                
            if contrib > 0:
                new_lot_value = net_contrib * (1 + self.ret) * (1 - fee_balance_rate)
                self.priv_lots.append({'basis': contrib, 'value': new_lot_value})
                
            self.priv_balance = sum(lot['value'] for lot in self.priv_lots)
            self.priv_basis = sum(lot['basis'] for lot in self.priv_lots)
            
        elif self.current_year_age < self.priv_payout_age:
            for lot in self.priv_lots:
                lot['value'] = lot['value'] * (1 + self.ret) * (1 - fee_balance_rate)
            self.priv_balance = sum(lot['value'] for lot in self.priv_lots)
            self.priv_basis = sum(lot['basis'] for lot in self.priv_lots)
            
        elif self.current_year_age <= self.priv_payout_end_age:
            for lot in self.priv_lots:
                lot['value'] = lot['value'] * (1 + self.ret) * (1 - fee_balance_rate)
            self.priv_balance = sum(lot['value'] for lot in self.priv_lots)
            self.priv_basis = sum(lot['basis'] for lot in self.priv_lots)

            net_ret = self.ret - fee_balance_rate
            periods_remaining = self.priv_payout_end_age - self.current_year_age + 1
            
            if net_ret != 0:
                priv_annuity = (net_ret * self.priv_balance) / (1 - (1+net_ret)**-periods_remaining)
            else:
                priv_annuity = self.priv_balance / periods_remaining
            
            if self.current_year_age == self.priv_payout_end_age:
                payout = self.priv_balance
            else:
                payout = min(priv_annuity, self.priv_balance)
                
            priv_payout_gross = payout
            
            remaining_to_withdraw = payout
            basis_withdrawn = 0.0
            
            new_priv_lots = []
            for lot in self.priv_lots:
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
                    
            self.priv_lots = new_priv_lots
            self.priv_balance = sum(lot['value'] for lot in self.priv_lots)
            self.priv_basis = sum(lot['basis'] for lot in self.priv_lots)
            
            gain = payout - basis_withdrawn
            taxable_gain = gain * (1 - 0.15) * 0.50
            
        else:
            self.priv_balance = 0.0
            self.priv_basis = 0.0
            self.priv_lots = []
            priv_payout_gross = 0.0
            taxable_gain = 0.0
            
        return priv_payout_gross, taxable_gain

    def _calc_gkv(self, user_salary_gross: float, state_pension_gross: float, priv_payout_gross: float) -> Tuple[float, float, float, bool]:
        """Calculates health insurance (GKV) costs and related base incomes."""
        gkv_cost = 0.0
        gkv_rate = (self.params['kv_rate'] + self.params['pv_rate']) / 100.0
        kvdr_kv_rate = (self.params['kv_rate'] / 2.0) / 100.0
        kvdr_pv_rate = self.params['pv_rate'] / 100.0
        
        bbg_gkv = 69750 * self.deflator
        min_gkv_income = 14140 * self.deflator 
        
        is_employed = (self.current_year_age < self.early_ret_age) or (self.do_partial_ret and self.current_year_age < self.final_ret_age)
        is_privatier = (not is_employed) and (self.current_year_age < self.state_ret_age)
        
        current_assessed_income_for_gkv = 0.0
        base_income_for_gkv = 0.0
        
        if self.current_year_age >= self.state_ret_age:
            if self.params['gkv_status'] == 'KVdR':
                gkv_cost = state_pension_gross * (kvdr_kv_rate + kvdr_pv_rate)
            else:
                # In voluntary mode, all income (state pension, private pension, stock gains)
                # is subject to the full GKV rate up to the BBG.
                # Stock gains from withdrawals are added later in _calc_stock_market.
                base_income_for_gkv = state_pension_gross + priv_payout_gross 
                current_assessed_income_for_gkv = max(base_income_for_gkv, min_gkv_income)
                gkv_cost = min(current_assessed_income_for_gkv, bbg_gkv) * gkv_rate
        elif is_privatier:
            base_income_for_gkv = priv_payout_gross
            current_assessed_income_for_gkv = max(base_income_for_gkv, min_gkv_income)
            gkv_cost = min(current_assessed_income_for_gkv, bbg_gkv) * gkv_rate
                
        return gkv_cost, base_income_for_gkv, min_gkv_income, is_privatier

    def _calc_income_taxes(self, user_salary_gross: float, state_pension_gross: float, taxable_gain: float, gkv_cost: float) -> Tuple[float, float, float, float]:
        """Calculates income taxes, distributing them proportionally among sources."""
        salary_gkv_deduction = user_salary_gross * 0.10 if user_salary_gross > 0 else 0.0
        
        nominal_taxable_income_total = max(0, user_salary_gross + state_pension_gross + taxable_gain - gkv_cost - salary_gkv_deduction)
        real_taxable_income_total = nominal_taxable_income_total / self.deflator
        real_tax_total = calc_income_tax_2026(real_taxable_income_total)
        total_nominal_income_tax = real_tax_total * self.deflator

        total_taxable_before_deductions = user_salary_gross + state_pension_gross + taxable_gain
        if total_taxable_before_deductions > 0:
            salary_tax = total_nominal_income_tax * (user_salary_gross / total_taxable_before_deductions)
            state_tax = total_nominal_income_tax * (state_pension_gross / total_taxable_before_deductions)
            priv_tax = total_nominal_income_tax * (taxable_gain / total_taxable_before_deductions)
        else:
            salary_tax = 0.0
            state_tax = 0.0
            priv_tax = 0.0
            
        return salary_tax, state_tax, priv_tax, salary_gkv_deduction

    def _calc_shortfall(self, user_salary_gross: float, state_pension_gross: float, priv_payout_gross: float, salary_tax: float, state_tax: float, priv_tax: float, salary_gkv_deduction: float, gkv_cost: float) -> float:
        """Determines the gap between required net income and the net income realized so far."""
        target_phase_started = self.current_year_age >= min(self.early_ret_age, self.priv_payout_age)
        shortfall = 0.0
        if target_phase_started:
            net_income_so_far = max(0, user_salary_gross + state_pension_gross + priv_payout_gross - salary_tax - state_tax - priv_tax - salary_gkv_deduction - gkv_cost)
            target_net_nominal = (self.params['target_net_income'] * 12) * self.deflator
            shortfall = max(0, target_net_nominal - net_income_so_far)
        return shortfall

    def _calc_stock_market(self, shortfall: float, is_privatier: bool, base_income_for_gkv: float, min_gkv_income: float, current_gkv_cost: float) -> Tuple[float, float, float, float]:
        """Calculates stock market growth, contributions, taxes, and handles required withdrawals."""
        stock_start = self.stock_balance
        stock_tax_vp = 0.0
        stock_tax_withdrawal = 0.0
        stock_withdrawal = 0.0
        additional_gkv = 0.0
        gkv_rate = (self.params['kv_rate'] + self.params['pv_rate']) / 100.0
        bbg_gkv = 69750 * self.deflator
        
        for lot in self.stock_lots:
            lot['value'] *= (1 + self.ret)
            
        if self.current_year_age < self.early_ret_age:
            # Accumulation phase
            contrib = self.params['stock_monthly'] * 12 * self.deflator
            
            etf_switches = self.params.get('etf_switches', 0)
            num_etfs = etf_switches + 1
            accumulation_years = self.early_ret_age - self.age
            if accumulation_years > 0:
                year_index = self.current_year_age - self.age - 1
                etf_id = int(year_index / (accumulation_years / num_etfs))
                etf_id = min(etf_id, etf_switches)
            else:
                etf_id = 0

            if contrib > 0:
                self.stock_lots.append({'basis': contrib, 'value': contrib, 'etf_id': etf_id})
            
            stock_balance_before_vp = sum(lot['value'] for lot in self.stock_lots)
            vp_tax, self.sparerpauschbetrag = calc_vorabpauschale(stock_start, stock_balance_before_vp, self.params['basiszinssatz']/100.0, self.sparerpauschbetrag, contrib=contrib)
            stock_tax_vp = vp_tax
            
            if stock_balance_before_vp > 0:
                vp_base_total = min(stock_start * (self.params['basiszinssatz']/100.0) * 0.7, max(0, stock_balance_before_vp - stock_start - contrib))
                for lot in self.stock_lots:
                    fraction = lot['value'] / stock_balance_before_vp
                    lot['basis'] += vp_base_total * fraction
                    lot['value'] -= vp_tax * fraction
            self.stock_balance = sum(lot['value'] for lot in self.stock_lots)
        else:
            # Retirement phase
            stock_balance_before_vp = sum(lot['value'] for lot in self.stock_lots)
            vp_tax, self.sparerpauschbetrag = calc_vorabpauschale(stock_start, stock_balance_before_vp, self.params['basiszinssatz']/100.0, self.sparerpauschbetrag)
            stock_tax_vp = vp_tax
            
            if stock_balance_before_vp > 0:
                vp_base_total = min(stock_start * (self.params['basiszinssatz']/100.0) * 0.7, max(0, stock_balance_before_vp - stock_start))
                for lot in self.stock_lots:
                    fraction = lot['value'] / stock_balance_before_vp
                    lot['basis'] += vp_base_total * fraction
                    lot['value'] -= vp_tax * fraction
            self.stock_balance = sum(lot['value'] for lot in self.stock_lots)
            
            if shortfall > 0:
                is_voluntary = is_privatier or (self.current_year_age >= self.state_ret_age and self.params['gkv_status'] != 'KVdR')
                
                ordered_lots = []
                for current_etf in range(self.params.get('etf_switches', 0), -1, -1):
                    ordered_lots.extend([lot for lot in self.stock_lots if lot.get('etf_id', 0) == current_etf])
                
                best_gross = self._find_optimal_withdrawal(
                    shortfall, ordered_lots, is_voluntary, base_income_for_gkv,
                    min_gkv_income, gkv_rate, bbg_gkv, current_gkv_cost
                )
                
                stock_withdrawal = best_gross
                gain_portion = 0.0
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
                    
                self.stock_lots = [lot for lot in self.stock_lots if lot['value'] > 0.001]
                self.stock_balance = sum(lot['value'] for lot in self.stock_lots)
                
                used_freibetrag = min(gain_portion, self.sparerpauschbetrag)
                stock_tax_withdrawal = max(0, gain_portion - used_freibetrag) * 0.26375
                self.sparerpauschbetrag -= used_freibetrag
                
                if is_voluntary:
                    total_income = base_income_for_gkv + gain_portion
                    new_assessed = max(total_income, min_gkv_income)
                    additional_gkv = max(0, min(new_assessed, bbg_gkv) * gkv_rate - current_gkv_cost)
            
        return stock_withdrawal, stock_tax_vp, stock_tax_withdrawal, additional_gkv

    def _find_optimal_withdrawal(self, shortfall: float, ordered_lots: List[Dict[str, Any]], is_voluntary: bool, base_income_for_gkv: float, min_gkv_income: float, gkv_rate: float, bbg_gkv: float, current_gkv_cost: float) -> float:
        """Finds the optimal gross withdrawal amount to satisfy the net shortfall using binary search."""
        temp_gross = self.stock_balance
        temp_gain = 0.0
        for lot in ordered_lots:
            lot_gain = max(0, lot['value'] - lot['basis']) * 0.70
            temp_gain += lot_gain
            
        used_freibetrag_temp = min(temp_gain, self.sparerpauschbetrag)
        taxable_temp = temp_gain - used_freibetrag_temp
        temp_tax = taxable_temp * 0.26375
        temp_gkv = 0.0
        
        if is_voluntary:
            total_income_temp = base_income_for_gkv + temp_gain
            new_assessed = max(total_income_temp, min_gkv_income)
            temp_gkv = max(0, min(new_assessed, bbg_gkv) * gkv_rate - current_gkv_cost)
            
        max_net = temp_gross - temp_tax - temp_gkv
        
        best_gross = self.stock_balance
        if max_net > shortfall:
            low = shortfall
            high = min(self.stock_balance, shortfall * 2.0)
            for _ in range(30):
                mid = (low + high) / 2.0
                temp_gross = mid
                temp_gain = 0.0
                for lot in ordered_lots:
                    if temp_gross <= 0: break
                    withdraw_from_lot = min(temp_gross, lot['value'])
                    fraction = withdraw_from_lot / lot['value']
                    basis_withdrawn = lot['basis'] * fraction
                    temp_gain += max(0, withdraw_from_lot - basis_withdrawn) * 0.70
                    temp_gross -= withdraw_from_lot
                    
                used_freibetrag_temp = min(temp_gain, self.sparerpauschbetrag)
                taxable_temp = temp_gain - used_freibetrag_temp
                temp_tax = taxable_temp * 0.26375
                
                temp_gkv = 0.0
                if is_voluntary:
                    total_income_temp = base_income_for_gkv + temp_gain
                    new_assessed = max(total_income_temp, min_gkv_income)
                    temp_gkv = max(0, min(new_assessed, bbg_gkv) * gkv_rate - current_gkv_cost)
                    
                net_temp = mid - temp_tax - temp_gkv
                
                if net_temp >= shortfall:
                    high = mid
                else:
                    low = mid
            best_gross = high
            
        return best_gross

    def _record_year(self, state_pension_gross: float, priv_payout_gross: float, stock_withdrawal: float, user_salary_gross: float, total_taxes: float, state_tax: float, priv_tax: float, salary_tax: float, stock_tax_withdrawal: float, stock_tax_vp: float, gkv_cost: float):
        """Appends the results of the simulated year to the records."""
        partial_salary_gross = user_salary_gross / self.deflator if (self.do_partial_ret and self.current_year_age >= self.early_ret_age and self.current_year_age < self.final_ret_age) else 0.0
        
        self.records.append({
            'Age': self.current_year_age,
            'Real Stock Balance': max(0, self.stock_balance) / self.deflator,
            'Real Priv Pension Balance': max(0, self.priv_balance) / self.deflator,
            'State Pension (Gross)': state_pension_gross / self.deflator,
            'Priv Payout (Gross)': priv_payout_gross / self.deflator,
            'Stock Withdrawal (Gross)': stock_withdrawal / self.deflator,
            'Partial Salary (Gross)': partial_salary_gross,
            'Total Taxes & GKV': total_taxes / self.deflator,
            'State Tax': state_tax / self.deflator,
            'Priv Tax': priv_tax / self.deflator,
            'Salary Tax': salary_tax / self.deflator,
            'Stock Tax': stock_tax_withdrawal / self.deflator,
            'Vorabpauschale': stock_tax_vp / self.deflator,
            'GKV Cost': gkv_cost / self.deflator,
            'Rentenpunkte': self.ep
        })


def simulate_wealth(params: Dict[str, Any]) -> pd.DataFrame:
    """
    Simulates wealth over time using the given parameters.
    
    Args:
        params: Dictionary containing simulation parameters.
        
    Returns:
        A pandas DataFrame containing the simulated wealth records per year.
    """
    sim = WealthSimulation(params)
    return sim.run()

def calculate_flat_savings_equivalent(params: Dict[str, Any]) -> Tuple[float, float]:
    """
    Calculates the equivalent flat monthly savings rate that yields the same nominal 
    contribution future value as the inflation-adjusted savings, avoiding the need 
    to increase monthly deposits each year.
    
    Args:
        params: Dictionary containing simulation parameters.
        
    Returns:
        A tuple containing the stock flat equivalent and the private pension flat equivalent.
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
