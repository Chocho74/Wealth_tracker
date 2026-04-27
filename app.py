import streamlit as st
import plotly.express as px
from calculations import simulate_wealth, calculate_flat_savings_equivalent

def main():
    st.set_page_config(page_title="Deutscher Rentenplaner", layout="wide", page_icon="📈")
    st.title("Deutsches Vermögens- & Rentenprojektions-Tool")
    st.markdown("""
    Dieses Tool modelliert den Aufbau und die Entnahme Ihrer Säulen der Altersvorsorge. 
    Es berücksichtigt die **Vorabpauschale**, das **Halbeinkünfteverfahren (12/62)** und den wichtigen Unterschied zwischen **KVdR** und **freiwilliger GKV**.
    """)

    with st.sidebar:
        st.header("1. Persönliche Daten")
        current_age = st.number_input("Aktuelles Alter", min_value=18, max_value=80, value=30)
        early_retirement_age = st.number_input("Gewünschtes Renteneintrittsalter (Frührente)", min_value=50, max_value=67, value=67)
        end_age = st.number_input("Endalter (Lebenserwartung)", min_value=70, max_value=120, value=95)
        salary = st.number_input("Aktuelles Bruttogehalt (€/Jahr)", value=60000, step=1000)
        partial_salary = st.number_input("Gehalt in Altersteilzeit (62-67) (€/Jahr)", value=30000, step=1000)
        target_net = st.number_input("Ziel-Nettoeinkommen im Ruhestand (€/Monat)", value=3000, step=100)
        
        st.header("2. Wirtschaftliche Annahmen")
        inflation = st.number_input("Inflationsrate (%)", value=2.0, step=0.1)
        return_pre = st.number_input("Rendite vor Rentenbeginn (%)", value=6.0, step=0.1)
        return_post = st.number_input("Rendite im Ruhestand (%)", value=4.0, step=0.1)
        basiszinssatz = st.number_input("Basiszinssatz Vorabpauschale 2026 (%)", value=3.20, step=0.1)
        
        st.header("3. Aktienmarkt (Depot)")
        stock_initial = st.number_input("Aktueller Depotbestand (€)", value=50000, step=1000)
        stock_monthly = st.number_input("Monatliche Sparrate (€)", value=500, step=50)
        
        st.header("4. Private Rente (Schicht 3)")
        priv_initial = st.number_input("Aktuelles Rentenguthaben (€)", value=10000, step=1000)
        priv_monthly = st.number_input("Monatlicher Beitrag (€)", value=200, step=50)
        priv_fee_contrib = st.number_input("Gebühr auf Einzahlungen (%)", value=0.50, step=0.10)
        priv_fee_balance = st.number_input("Jährliche Gebühr auf Guthaben (%)", value=0.22, step=0.01)
        
        st.header("5. Gesetzliche Rente")
        current_ep = st.number_input("Aktuelle Rentenpunkte (EP)", value=10.0, step=1.0)
        
        st.header("6. Krankenversicherung")
        gkv_status_display = st.selectbox("GKV-Status im Ruhestand", ["KVdR", "Freiwillig"])
        st.caption("KVdR: GKV nur auf gesetzliche Rente. Freiwillig: GKV auf das GESAMTE Einkommen (Depot, private Rente).")
        kv_rate = st.number_input("GKV-Beitragssatz + Zusatzbeitrag (%)", value=17.5, step=0.1)
        pv_rate = st.number_input("Beitragssatz Pflegeversicherung (PV) (%)", value=3.6, step=0.1)


    params = {
        'current_age': current_age, 'end_age': end_age, 'early_retirement_age': early_retirement_age, 'salary': salary, 'partial_salary': partial_salary, 'target_net_income': target_net,
        'inflation': inflation, 'return_pre': return_pre, 'return_post': return_post, 'basiszinssatz': basiszinssatz,
        'stock_initial': stock_initial, 'stock_monthly': stock_monthly,
        'priv_initial': priv_initial, 'priv_monthly': priv_monthly,
        'priv_fee_contrib': priv_fee_contrib, 'priv_fee_balance': priv_fee_balance,
        'current_ep': current_ep,
        'gkv_status': 'KVdR' if gkv_status_display == 'KVdR' else 'Voluntary', 
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
        fig.add_vline(x=early_retirement_age, line_dash="dash", line_color="purple", annotation_text=f"Alter {early_retirement_age} (Frührente)", annotation_position="top left")
        fig.add_vline(x=62, line_dash="dash", line_color="red", annotation_text="Alter 62 (Priv. Auszahlung)", annotation_position="bottom left")
        fig.add_vline(x=67, line_dash="dash", line_color="orange", annotation_text="Alter 67 (Gesetzl. Rente)", annotation_position="top right")
        
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
        st.header("Erklärung der Berechnungen und steuerlichen Details")
        
        st.markdown("""
        **1. Inflation und Kaufkraftbereinigung**  
        Alle angezeigten Werte (Vermögen, Renten, Entnahmen) sind **inflationsbereinigt**. Das bedeutet, das Tool rechnet zukünftige Summen in die **heutige Kaufkraft** um. So können Sie direkt sehen, was Ihr zukünftiges Einkommen in heutigen Preisen wert ist.

        **2. Gesetzliche Rente**  
        Die gesetzliche Rente wird anhand Ihrer gesammelten **Rentenpunkte (Entgeltpunkte, EP)** berechnet. Bis zu Ihrem Renteneintrittsalter sammeln Sie durch Ihr Gehalt weitere Punkte (gedeckelt durch die Beitragsbemessungsgrenze). Jeder Punkt wird mit dem aktuellen Rentenwert multipliziert, um Ihre Bruttorente zu ermitteln.

        **3. Private Rentenversicherung & Halbeinkünfteverfahren (12/62-Regel)**  
        Die private Rentenversicherung (Schicht 3) hat in diesem Tool folgende feste Phasen:
        - **Ansparphase:** Bis Alter 50 werden monatliche Beiträge eingezahlt.
        - **Ruhephase:** Von 50 bis 62 wächst das Kapital ohne weitere Einzahlungen.
        - **Auszahlungsphase:** Ab Alter 62 bis 85 wird das Kapital verrentet und monatlich ausgezahlt.
        
        **Das Halbeinkünfteverfahren (12/62-Regel):**  
        Wenn ein privater Rentenvertrag mindestens 12 Jahre lief und die Auszahlung frühestens ab dem 62. Lebensjahr erfolgt, greift das Halbeinkünfteverfahren. 
        Hierbei wird nicht die gesamte Auszahlung besteuert, sondern nur der **Ertragsanteil** (Auszahlung minus eingezahlte Beiträge). Von diesem Ertrag sind zudem 15% pauschal steuerfrei (Teilfreistellung). Vom verbleibenden Betrag müssen Sie **nur die Hälfte (50%)** mit Ihrem persönlichen Einkommensteuersatz versteuern. Das macht die private Rente in der Auszahlungsphase oft steuerlich sehr attraktiv.

        **4. Aktienmarkt (Depot) & Vorabpauschale**  
        Ihr ETF- oder Aktiendepot wächst jährlich um die angenommene Rendite. Steuern fallen nicht erst beim Verkauf an, sondern jährlich durch die **Vorabpauschale**:
        - Die Vorabpauschale besteuert fiktive Erträge Ihres Depots. 
        - Für Aktienfonds gilt eine **Teilfreistellung von 30%**, d.h. 30% der Erträge sind steuerfrei.
        - Auf den steuerpflichtigen Teil wird Ihr **Sparerpauschbetrag** (1.000 € pro Jahr) angerechnet.
        - Nur der Betrag, der darüber hinausgeht, wird mit der Abgeltungsteuer (inkl. Soli ca. 26,375 %) versteuert.
        Bei Entnahmen aus dem Depot im Ruhestand (um Ihr Ziel-Nettoeinkommen zu erreichen) wird ebenfalls nur der Gewinnanteil versteuert, abzüglich eventuell noch vorhandenem Sparerpauschbetrag.

        **5. Krankenversicherung (GKV) und Frührente (Privatier)**  
        Ein entscheidender Kostenfaktor im Ruhestand ist die Krankenversicherung:
        - **KVdR (Krankenversicherung der Rentner):** Wenn Sie die Voraussetzungen für die KVdR erfüllen, zahlen Sie im gesetzlichen Rentenalter GKV-Beiträge **nur auf Ihre gesetzliche Rente** (und der Staat übernimmt die Hälfte). Ihr privates Rentenguthaben und Ihr Depot bleiben GKV-frei!
        - **Freiwillig gesetzlich versichert:** Sind Sie nicht in der KVdR oder gehen Sie in **Frührente (als Privatier)**, stuft die Krankenkasse Sie als freiwillig versichert ein. In diesem Fall müssen Sie GKV- und Pflegebeiträge (ca. 20-21%) auf Ihr **gesamtes Einkommen** zahlen, also auch auf Auszahlungen aus der privaten Rente und auf Kapitalerträge aus dem Depot. Dies gilt maximal bis zur Beitragsbemessungsgrenze der GKV. Im Tool wird dies in der Phase der Frührente exakt berücksichtigt.

        **6. Angenommene Renditen und Anlagezeiträume**  
        Das Tool verwendet zwei unterschiedliche Renditen, um das typische Risiko-Rendite-Profil im Lebenszyklus abzubilden:
        - **Rendite vor Rentenbeginn:** Diese (meist höhere) Rendite wird für die Aufbauphase angenommen. Sie gilt einheitlich für Ihr **Aktiendepot** und Ihr **privates Rentenguthaben**, solange Sie arbeiten – genauer gesagt, bis zu dem von Ihnen festgelegten *Gewünschten Renteneintrittsalter (Frührente)*.
        - **Rendite im Ruhestand:** Exakt ab dem Jahr, in dem Sie in Rente gehen (Frührente oder gesetzliche Rente), wechselt das Tool für beide Bausteine (Depot und private Rente) auf diese (meist niedrigere) Rendite. Dies simuliert den in der Praxis typischen "Shift", bei dem das Portfolio zur Absicherung der Entnahmen in risikoärmere Anlagen (wie z. B. Anleihen) umgeschichtet wird, die weniger Rendite bringen, aber sicherer sind.
        """)

if __name__ == "__main__":
    main()