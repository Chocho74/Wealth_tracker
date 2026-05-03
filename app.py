import streamlit as st
import plotly.express as px
import json
from calculations import simulate_wealth, calculate_flat_savings_equivalent

def load_params():
    if st.session_state.uploaded_file is not None:
        try:
            loaded = json.load(st.session_state.uploaded_file)
            allowed_keys = {
                'current_age', 'early_retirement_age', 'end_age', 'salary',
                'do_partial_retirement', 'partial_duration', 'partial_salary', 'target_net',
                'inflation', 'return_pre', 'return_post', 'basiszinssatz',
                'stock_initial', 'stock_monthly', 'etf_switches',
                'priv_initial', 'priv_monthly', 'priv_fee_contrib', 'priv_fee_balance',
                'current_ep', 'gkv_status_display', 'kv_rate', 'pv_rate'
            }
            for k, v in loaded.items():
                if k in allowed_keys:
                    st.session_state[k] = v
        except Exception as e:
            st.error(f"Fehler beim Laden der Datei: {e}")

def main():
    st.set_page_config(page_title="Deutscher Rentenplaner", layout="wide", page_icon="📈")
    st.title("Deutsches Vermögens- & Rentenprojektions-Tool")
    st.markdown("""
    Dieses Tool modelliert den Aufbau und die Entnahme Ihrer Säulen der Altersvorsorge. 
    Es berücksichtigt die **Vorabpauschale**, das **Halbeinkünfteverfahren (12/62)** und den wichtigen Unterschied zwischen **KVdR** und **freiwilliger GKV**.
    """)
    
    if 'show_disclaimer' not in st.session_state:
        st.session_state.show_disclaimer = False

    def toggle_disclaimer():
        st.session_state.show_disclaimer = not st.session_state.show_disclaimer

    st.button("⚠️ Disclaimer", on_click=toggle_disclaimer)

    if st.session_state.show_disclaimer:
        st.warning("""
        **Disclaimer (Haftungsausschluss):** Dieses Tool dient ausschließlich zu Informations- und Bildungszwecken. Es stellt keine Finanz-, Steuer- oder Rechtsberatung dar. 
        Die Berechnungen basieren auf den gesetzlichen Regelungen und Parametern des Jahres 2026, welche sich in Zukunft jederzeit ändern können. 
        Alle Ergebnisse sind stark vereinfachte Modellrechnungen und Schätzungen. Für die tatsächliche Richtigkeit, Vollständigkeit und Anwendbarkeit der Berechnungen auf Ihre persönliche Situation wird keine Gewähr übernommen.
        Bitte konsultieren Sie für verlässliche Planungen einen qualifizierten Steuerberater oder Finanzexperten.
        """)

    if 'show_info' not in st.session_state:
        st.session_state.show_info = False

    def toggle_info():
        st.session_state.show_info = not st.session_state.show_info

    st.button("ℹ️ INFO: Berechnungs- und Steuerdetails anzeigen", on_click=toggle_info)

    if st.session_state.show_info:
        st.info("""
### 💡 Allgemeine Berechnungsgrundlage (Inflation)
Alle internen Berechnungen des Tools finden in **nominalen Werten** statt (also unter Einbeziehung der Inflation über die Jahre). Um Ihnen jedoch ein intuitives Verständnis zu geben, werden alle ausgegebenen Zahlen (Vermögen, Steuern, Entnahmen) in die **heutige Kaufkraft (real)** zurückgerechnet.

### 1. Gesetzliche Rente (GRV)
Die gesetzliche Rente wird durch das Sammeln von **Rentenpunkten (Entgeltpunkten, EP)** simuliert.
* **Ansparphase:** Während Sie arbeiten, wird Ihr Bruttogehalt durch das Durchschnittsentgelt (ca. 51.944 € für 2026) geteilt, um Ihre jährlichen Rentenpunkte zu ermitteln. Das maximal anrechenbare Gehalt ist durch die Beitragsbemessungsgrenze (101.400 €) gedeckelt. Altersteilzeit wird ebenfalls unterstützt und bringt proportionale Punkte.
* **Auszahlungsphase (ab 67):** Jeder gesammelte Rentenpunkt ist monatlich 42,52 € wert (Rentenwert 2026).

### 2. Private Rentenversicherung
Die private Rente ist in drei Phasen unterteilt und nutzt steuerlich das attraktive **Halbeinkünfteverfahren (12/62-Regel)**:
* **Phase 1 (Bis Alter 50):** Sie zahlen monatlich ein. Nach Abzug einer Abschlussgebühr (z.B. 0,50%) wächst Ihr Geld am Kapitalmarkt, abzüglich einer laufenden Verwaltungsgebühr (z.B. 0,22%).
* **Phase 2 (Alter 50 bis 62):** Die Einzahlungen stoppen, aber das Kapital wächst weiter.
* **Phase 3 (Alter 62 bis 85):** Das Kapital wird als lebenslange Rente (bzw. bis Alter 85) ausgezahlt.
* **Besteuerung (12/62-Regel):** Da der Vertrag über 12 Jahre lief und erst ab Alter 62 ausgezahlt wird, ist nur der **Gewinn** steuerpflichtig. Der Gewinn ist definiert als die **Bruttoauszahlung minus dem proportionalen Anteil der ursprünglichen Einzahlungen**. Von diesem Gewinn sind nochmal 15% pauschal steuerfrei (Teilfreistellung). Die verbleibende Summe müssen Sie nur **zur Hälfte (50%)** mit Ihrem persönlichen Einkommensteuersatz versteuern.

### 3. Aktienmarkt (Depot) & Vorabpauschale
Das Depot wird präzise nach dem **FIFO-Prinzip (First-In, First-Out)** und mit den Regeln für die **Vorabpauschale** berechnet.
* **Vorabpauschale:** Diese "Vorab-Steuer" wird jährlich auf fiktive Erträge Ihres Depots berechnet (Basiszins 2026: 3,20%). Für Aktien-ETFs sind 30% steuerfrei. Die Steuer wird erst mit Ihrem Sparerpauschbetrag (1.000 €) verrechnet, bevor die tatsächliche Abgeltungsteuer (26,375%) greift. Gezahlte Vorabpauschalen werden beim späteren Verkauf steuermindernd angerechnet.
* **Entnahme im Ruhestand:** Das Tool berechnet automatisch, wie viel Sie aus dem Depot entnehmen müssen, um Ihre gewünschte Nettolücke zu schließen. Da die zu zahlenden Steuern und Krankenkassenbeiträge von der Höhe der Bruttoentnahme abhängen, nutzt das Tool im Hintergrund einen **binären Suchalgorithmus**, um exakt den Bruttobetrag zu finden, der nach allen Abzügen genau Ihr Nettoziel trifft. Nur der Gewinnanteil der verkauften Anteile wird besteuert (wiederum abzüglich 30% Teilfreistellung).
* **Tipp (ETF-Wechsel):** Um Steuern im Ruhestand zu optimieren, können Sie in der Ansparphase den besparten ETF in regelmäßigen Abständen wechseln. Im Ruhestand verkaufen Sie dann die jüngsten Anteile zuerst (LIFO-Strategie), was die Steuerlast deutlich senkt.

### 4. Kranken- und Pflegeversicherung (GKV/PV)
Die Krankenversicherung kann im Ruhestand einer der größten Kostenfaktoren sein.
* **Angestelltenphase:** Während Sie arbeiten, wird zur Ermittlung der Steuerbasis pauschal ein **Abzug von 10%** vom Bruttogehalt für die Sozialabgaben angenommen.
* **Privatier (Frührente vor Alter 67):** Wenn Sie nicht arbeiten, sind Sie "freiwillig gesetzlich versichert". Sie müssen auf **Ihr gesamtes Einkommen** (Depotgewinne, private Rente) volle Kranken- und Pflegebeiträge zahlen (bis zur Bemessungsgrenze von ca. 69.750 €/Jahr). Das Mindesteinkommen beträgt 14.140 €/Jahr.
* **Gesetzliche Rente (ab Alter 67):**
    * **KVdR (Krankenversicherung der Rentner):** Wenn Sie die Voraussetzungen erfüllen, zahlen Sie GKV-Beiträge **nur auf Ihre gesetzliche Rente** (und nur den halben Beitragssatz für die KV!). Depot und private Rente sind in der Krankenversicherung komplett **abgabenfrei**.
    * **Freiwillig versichert:** Erfüllen Sie die KVdR nicht, zahlen Sie auch im gesetzlichen Rentenalter auf **alle** Einkunftsarten den vollen Beitragssatz.

### 5. Einkommensteuer (ESt)
Das Tool nutzt den voraussichtlichen **Einkommensteuertarif 2026**. Die Steuerlast wird nach folgenden Progressionszonen berechnet:
* **Zone 1 (Grundfreibetrag):** 0 € bis 12.336 € (Steuerfrei)
* **Zone 2:** Bis 17.005 € (Eingangssteuersatz)
* **Zone 3:** Bis 66.760 € (Hauptprogressionszone)
* **Zone 4:** Bis 277.825 € (Spitzensteuersatz von pauschal 42%)
* **Zone 5:** Ab 277.826 € (Reichensteuer von pauschal 45%)

Die Gesamtsteuerlast auf alle Ihre Einkünfte wird in nominalen Werten berechnet und im Tool proportional auf Ihre Einkommensquellen aufgeteilt, um Ihnen ein exaktes Bild Ihrer Nettobelastung zu zeigen.
        """)

    with st.sidebar:
        st.header("📂 Parameter Speichern / Laden")
        st.file_uploader("Parameter laden (.json)", type=["json"], key="uploaded_file", on_change=load_params)

        # Initialize defaults in session state to avoid warning when loading json
        defaults = {
            'current_age': 30, 'early_retirement_age': 67, 'end_age': 95, 'salary': 60000,
            'do_partial_retirement': False, 'partial_duration': 2, 'partial_salary': 30000.0,
            'target_net': 3000, 'inflation': 2.0, 'return_pre': 6.0, 'return_post': 4.0,
            'basiszinssatz': 3.20, 'stock_initial': 50000, 'stock_monthly': 500, 'etf_switches': 0,
            'priv_initial': 10000, 'priv_monthly': 200, 'priv_fee_contrib': 0.50, 'priv_fee_balance': 0.22,
            'current_ep': 10.0, 'gkv_status_display': "KVdR", 'kv_rate': 17.5, 'pv_rate': 3.6
        }
        for k, v in defaults.items():
            if k not in st.session_state:
                st.session_state[k] = v
        
        st.header("1. Persönliche Daten")
        current_age = st.number_input("Aktuelles Alter", min_value=18, max_value=80, key="current_age")
        early_retirement_age = st.number_input("Gewünschtes Renteneintrittsalter (Frührente)", min_value=50, max_value=67, key="early_retirement_age")
        end_age = st.number_input("Endalter (Lebenserwartung)", min_value=70, max_value=120, key="end_age")
        salary = st.number_input("Aktuelles Bruttogehalt (€/Jahr)", step=1000, key="salary")
        
        do_partial_retirement = False
        final_retirement_age = early_retirement_age
        partial_salary = 0.0
        
        if early_retirement_age < 67:
            do_partial_retirement = st.checkbox("Nach dem Renteneintrittsalter in Altersteilzeit arbeiten?", key="do_partial_retirement")
            if do_partial_retirement:
                max_duration = 67 - early_retirement_age
                partial_duration = st.number_input("Dauer der Altersteilzeit (Jahre)", min_value=1, max_value=max_duration, step=1, key="partial_duration")
                final_retirement_age = early_retirement_age + partial_duration
                partial_salary = st.number_input("Geschätztes Bruttogehalt in Altersteilzeit (€/Jahr)", step=1000.0, key="partial_salary")
                
        target_net = st.number_input("Ziel-Nettoeinkommen im Ruhestand (€/Monat)", step=100, key="target_net")
        
        st.header("2. Wirtschaftliche Annahmen")
        inflation = st.number_input("Inflationsrate (%)", step=0.1, key="inflation")
        return_pre = st.number_input("Rendite vor Rentenbeginn (%)", step=0.1, key="return_pre")
        return_post = st.number_input("Rendite im Ruhestand (%)", step=0.1, key="return_post")
        basiszinssatz = st.number_input("Basiszinssatz Vorabpauschale 2026 (%)", step=0.1, key="basiszinssatz")
        
        st.header("3. Aktienmarkt (Depot)")
        stock_initial = st.number_input("Aktueller Depotbestand (€)", step=1000, key="stock_initial")
        stock_monthly = st.number_input("Monatliche Sparrate (€)", step=50, key="stock_monthly")
        etf_switches = st.number_input("Anzahl ETF-Wechsel in der Ansparphase", min_value=0, max_value=10, step=1, key="etf_switches")
        st.caption("LIFO-Strategie: Wenn Sie während der Ansparphase ETFs wechseln, wird im Ruhestand der jeweils jüngste ETF zuerst verkauft. Innerhalb des ETFs gilt das FIFO-Prinzip.")
        
        st.header("4. Private Rente (Schicht 3)")
        priv_initial = st.number_input("Aktuelles Rentenguthaben (€)", step=1000, key="priv_initial")
        priv_monthly = st.number_input("Monatlicher Beitrag (€)", step=50, key="priv_monthly")
        priv_fee_contrib = st.number_input("Gebühr auf Einzahlungen (%)", step=0.10, key="priv_fee_contrib")
        priv_fee_balance = st.number_input("Jährliche Gebühr auf Guthaben (%)", step=0.01, key="priv_fee_balance")
        
        st.header("5. Gesetzliche Rente")
        current_ep = st.number_input("Aktuelle Rentenpunkte (EP)", step=1.0, key="current_ep")
        
        st.header("6. Krankenversicherung")
        gkv_status_display = st.selectbox("GKV-Status im Ruhestand", ["KVdR", "Freiwillig"], key="gkv_status_display")
        st.caption("KVdR: GKV nur auf gesetzliche Rente. Freiwillig: GKV auf das GESAMTE Einkommen (Depot, private Rente).")
        kv_rate = st.number_input("GKV-Beitragssatz + Zusatzbeitrag (%)", step=0.1, key="kv_rate")
        pv_rate = st.number_input("Beitragssatz Pflegeversicherung (PV) (%)", step=0.1, key="pv_rate")

        # Create dict to save
        save_dict = {
            "current_age": current_age, "early_retirement_age": early_retirement_age, "end_age": end_age,
            "salary": salary, "do_partial_retirement": do_partial_retirement, "partial_duration": partial_duration if 'partial_duration' in locals() else 2,
            "partial_salary": partial_salary, "target_net": target_net,
            "inflation": inflation, "return_pre": return_pre, "return_post": return_post, "basiszinssatz": basiszinssatz,
            "stock_initial": stock_initial, "stock_monthly": stock_monthly, "etf_switches": etf_switches,
            "priv_initial": priv_initial, "priv_monthly": priv_monthly, "priv_fee_contrib": priv_fee_contrib, "priv_fee_balance": priv_fee_balance,
            "current_ep": current_ep, "gkv_status_display": gkv_status_display, "kv_rate": kv_rate, "pv_rate": pv_rate
        }
        
        st.download_button(
            label="💾 Aktuelle Parameter speichern",
            data=json.dumps(save_dict, indent=4),
            file_name="rentenplaner_params.json",
            mime="application/json",
            use_container_width=True
        )


    params = {
        'current_age': current_age, 'end_age': end_age, 'early_retirement_age': early_retirement_age, 
        'salary': salary, 'partial_salary': partial_salary, 'target_net_income': target_net,
        'do_partial_ret': do_partial_retirement, 'final_ret_age': final_retirement_age,
        'inflation': inflation, 'return_pre': return_pre, 'return_post': return_post, 'basiszinssatz': basiszinssatz,
        'stock_initial': stock_initial, 'stock_monthly': stock_monthly, 'etf_switches': etf_switches,
        'priv_initial': priv_initial, 'priv_monthly': priv_monthly,
        'priv_fee_contrib': priv_fee_contrib, 'priv_fee_balance': priv_fee_balance,
        'current_ep': current_ep,
        'gkv_status': gkv_status_display, 
        'kv_rate': kv_rate, 'pv_rate': pv_rate
    }

    if st.button("Simulation starten", type="primary", use_container_width=True):
        df = simulate_wealth(params)
        
        # Calculate equivalent flat savings rates
        stock_flat, priv_flat = calculate_flat_savings_equivalent(params)
        
        st.info(f"💡 **Info zur Inflationsanpassung:** Die Simulation geht davon aus, dass Sie Ihre monatlichen Sparraten jährlich um die Inflation ({inflation}%) erhöhen. Möchten Sie Ihre Sparrate stattdessen konstant halten, müssten Sie von Beginn an **{stock_flat:,.0f} € ins Depot** und **{priv_flat:,.0f} € in die private Rente** sparen, um exakt dasselbe nominale Endkapital zu Rentenbeginn zu erreichen.")
        
        # Translate dataframe columns for German UI
        df = df.rename(columns={
            'Age': 'Alter',
            'Real Stock Balance': 'Realer Depotbestand',
            'Real Priv Pension Balance': 'Reales privates Rentenguthaben',
            'State Pension (Gross)': 'Reale Gesetzliche Rente (Brutto)',
            'Priv Payout (Gross)': 'Reale Private Auszahlung (Brutto)',
            'Stock Withdrawal (Gross)': 'Reale Depotentnahme (Brutto)',
            'Partial Salary (Gross)': 'Gehalt Altersteilzeit (Brutto)',
            'Total Taxes & GKV': 'Reale Steuern & GKV (Gesamt)',
            'State Tax': 'Steuer auf ges. Rente',
            'Priv Tax': 'Steuer auf priv. Rente',
            'Stock Tax': 'Steuer auf Depotentnahme',
            'Salary Tax': 'Steuer auf Gehalt',
            'Vorabpauschale': 'Vorabpauschale (Depot)',
            'GKV Cost': 'GKV & PV Beiträge',
            'Rentenpunkte': 'Rentenpunkte (EP)'
        })
        
        st.subheader("Vermögensentwicklung & Entnahme (Kaufkraftbereinigt)")
        st.markdown("Dieses Diagramm zeigt Ihr inflationsbereinigtes Kapital und stellt die tatsächliche heutige Kaufkraft Ihres Geldes dar.")
        
        # Stacked Area Chart Data Prep
        df_plot = df[['Alter', 'Realer Depotbestand', 'Reales privates Rentenguthaben']].copy()
        
        fig = px.area(df_plot, x='Alter', y=['Reales privates Rentenguthaben', 'Realer Depotbestand'], 
                      title=f"Kapitalprojektion (Kaufkraftbereinigt)",
                      labels={'value': 'Vermögen in heutiger Kaufkraft (€)', 'variable': 'Säule', 'Alter': 'Alter'},
                      color_discrete_sequence=['#1f77b4', '#2ca02c'])
        
        # Add Retirement lines
        fig.add_vline(x=early_retirement_age, line_dash="dash", line_color="purple", annotation_text=f"Alter {early_retirement_age} (Ende Vollzeit)", annotation_position="top left")
        if do_partial_retirement:
             fig.add_vline(x=final_retirement_age, line_dash="dash", line_color="magenta", annotation_text=f"Alter {final_retirement_age} (Ende Teilzeit)", annotation_position="top right")
        fig.add_vline(x=62, line_dash="dash", line_color="red", annotation_text="Alter 62 (Priv. Auszahlung)", annotation_position="bottom left")
        fig.add_vline(x=67, line_dash="dash", line_color="orange", annotation_text="Alter 67 (Gesetzl. Rente)", annotation_position="bottom right")
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Einkommensströme im Ruhestand (Brutto, Kaufkraftbereinigt)")
        st.markdown("Dieses Diagramm zeigt die Zusammensetzung Ihrer monatlichen Entnahmen und Renten (Durchschnitt pro Jahr) ab Beginn der Auszahlungsphase in heutiger Kaufkraft.")
        
        df_payout = df[df['Alter'] >= early_retirement_age].copy()
        df_payout['Reale Gesetzliche Rente (Brutto)'] /= 12
        df_payout['Reale Private Auszahlung (Brutto)'] /= 12
        df_payout['Gehalt Altersteilzeit (Brutto)'] /= 12
        df_payout['Reale Depotentnahme (Brutto)'] /= 12
        
        fig_payout = px.bar(df_payout, x='Alter', y=['Reale Gesetzliche Rente (Brutto)', 'Reale Private Auszahlung (Brutto)', 'Gehalt Altersteilzeit (Brutto)', 'Reale Depotentnahme (Brutto)'],
                            title="Monatliche Gesamtauszahlung (Kaufkraftbereinigt)",
                            labels={'value': 'Auszahlung in heutiger Kaufkraft (€/Monat)', 'variable': 'Einkommensquelle', 'Alter': 'Alter'},
                            color_discrete_sequence=['#ff7f0e', '#1f77b4', '#8c564b', '#2ca02c'])
        st.plotly_chart(fig_payout, use_container_width=True)

        st.subheader("Steuern & Abgaben im Ruhestand (Kaufkraftbereinigt)")
        st.markdown("Dieses Diagramm zeigt Ihre monatlichen Steuer- und Krankenkassenbelastungen (Durchschnitt pro Jahr) ab Beginn der Auszahlungsphase in heutiger Kaufkraft.")
        
        df_taxes = df[df['Alter'] >= early_retirement_age].copy()
        df_taxes['Steuer auf ges. Rente'] /= 12
        df_taxes['Steuer auf priv. Rente'] /= 12
        df_taxes['Steuer auf Gehalt'] /= 12
        df_taxes['Steuer auf Depotentnahme'] /= 12
        df_taxes['Vorabpauschale (Depot)'] /= 12
        df_taxes['GKV & PV Beiträge'] /= 12
        
        fig_taxes = px.bar(df_taxes, x='Alter', y=['Steuer auf ges. Rente', 'Steuer auf priv. Rente', 'Steuer auf Gehalt', 'Steuer auf Depotentnahme', 'Vorabpauschale (Depot)', 'GKV & PV Beiträge'],
                            title="Monatliche Steuern & Abgaben (Kaufkraftbereinigt)",
                            labels={'value': 'Abgaben in heutiger Kaufkraft (€/Monat)', 'variable': 'Abgabenart', 'Alter': 'Alter'},
                            color_discrete_sequence=['#d62728', '#9467bd', '#1f77b4', '#8c564b', '#17becf', '#e377c2'])
        st.plotly_chart(fig_taxes, use_container_width=True)
        
        st.subheader("Detaillierte jährliche Projektion")
        st.dataframe(df.round(0), use_container_width=True)

    st.markdown("---")
    st.markdown("<div style='text-align: center; color: gray;'><small>Bei Fragen oder Anregungen kontaktieren Sie mich gerne unter: <a href='mailto:ericguenl@gmail.com'>ericguenl@gmail.com</a> | <a href='https://github.com/Chocho74/Wealth_tracker' target='_blank'>Projekt auf GitHub ansehen</a></small></div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()