import json
from nicegui import ui, app, events
import plotly.express as px
import pandas as pd
from calculations import simulate_wealth, calculate_flat_savings_equivalent

class AppState:
    def __init__(self):
        self.current_age = 30
        self.early_retirement_age = 67
        self.end_age = 95
        self.salary = 60000
        self.do_partial_retirement = False
        self.partial_duration = 2
        self.partial_salary = 30000.0
        self.target_net = 3000
        self.inflation = 2.0
        self.return_pre = 6.0
        self.return_post = 4.0
        self.basiszinssatz = 3.20
        self.stock_initial = 50000
        self.stock_monthly = 500
        self.etf_switches = 0
        self.priv_initial = 10000
        self.priv_monthly = 200
        self.priv_fee_contrib = 0.50
        self.priv_fee_balance = 0.22
        self.current_ep = 10.0
        self.gkv_status_display = "KVdR"
        self.kv_rate = 17.5
        self.pv_rate = 3.6

def parse_money(v):
    try: return float(str(v).replace('.', '').replace(',', '.'))
    except: return 0.0

def format_money(v):
    try: return str(int(float(v)))
    except: return ''

@ui.page('/')
def main_page():
    state = AppState()
    
    ui.page_title("Deutscher Rentenplaner")
    
    # Header
    with ui.header().classes('bg-blue-600 text-white p-4 shadow-md flex justify-between items-center') as header:
        ui.label('Deutsches Vermögens- & Rentenprojektions-Tool').classes('font-bold text-xl')
        ui.space()
        dark = ui.dark_mode()
        ui.switch('Dark Mode').bind_value(dark, 'value')
    
    # Main Content
    with ui.column().classes('w-full max-w-6xl mx-auto p-4 md:p-8 gap-4'):
        ui.add_head_html('''<style>
            /* Überschreibe die Quasar-Standardklassen für Labels, Inputs und Checkboxen */
            .q-field__label, .q-field__native, .q-checkbox__label { 
                font-size: 1.1rem !important; 
                font-weight: 700 !important; 
            }
            /* Erhöhe die Gesamthöhe des Eingabefeldes, um mehr Platz zu schaffen */
            .q-field__control {
                min-height: 65px !important;
            }
            /* Schiebe den eigentlichen Eingabewert (z.B. "30") weiter nach unten */
            .q-field--labeled .q-field__native {
                padding-top: 32px !important; 
                padding-bottom: 8px !important;
            }
            /* Schiebe das Label (z.B. "Aktuelles Alter") weiter nach oben */
            .q-field--float .q-field__label {
                transform: translateY(-60%) scale(0.85) !important;
            }
            .body--dark .q-field__label, .body--dark .q-field__native { color: #f3f4f6 !important; }
            .body--light .q-field__label, .body--light .q-checkbox__label, .body--light .q-field__native { color: #1f2937 !important; }
        </style>''')

        ui.label("Deutsches Vermögens- & Rentenprojektions-Tool").classes('text-3xl font-extrabold text-gray-800 dark:text-gray-200 mb-2')
        ui.label("Dieses Tool modelliert den Aufbau und die Entnahme Ihrer Säulen der Altersvorsorge. Es berücksichtigt unter anderem die Vorabpauschale, das Halbeinkünfteverfahren (12/62) und den Unterschied zwischen KVdR und freiwilliger GKV.").classes('text-lg text-gray-600 dark:text-gray-400 mb-4')
        
        # Settings Section
        ui.label("⚙️ Einstellungen & Parameter").classes('text-2xl font-bold mt-4 border-b-2 border-gray-200 pb-2 w-full')
        
        # Load/Save Row
        with ui.row().classes('w-full items-center bg-gray-100 dark:bg-slate-800 p-4 rounded-lg shadow-inner justify-between mb-4 flex-wrap gap-4'):
            with ui.row().classes('items-center gap-4'):
                ui.label("📂 Parameter verwalten:").classes('font-bold text-gray-700 dark:text-gray-300')
                async def handle_upload(e: events.UploadEventArguments):
                    try:
                        content = await e.file.read()
                        data = json.loads(content.decode('utf-8'))
                        for k, v in data.items():
                            if hasattr(state, k):
                                setattr(state, k, v)
                        ui.notify("Parameter erfolgreich geladen!", type='positive')
                        ui.update()
                    except Exception as ex:
                        ui.notify(f"Fehler beim Laden: {ex}", type='negative')
                
                ui.upload(on_upload=handle_upload, label="Laden (.json)", auto_upload=True).props('accept=.json max-files=1 max-file-size=51200').classes('w-48')
            
            def download_params():
                data = json.dumps(state.__dict__, indent=4)
                ui.download(data.encode('utf-8'), 'rentenplaner_params.json')
                
            ui.button("💾 Aktuelle Werte speichern", on_click=download_params, color='secondary').classes('shadow-sm')

        # Input Grid
        with ui.grid(columns=1).classes('w-full gap-6 md:grid-cols-2 lg:grid-cols-3'):
            with ui.expansion('1. Persönliche Daten', icon='person').classes('w-full bg-gray-100 dark:bg-gray-800 shadow-md rounded-md text-black dark:text-white').props('default-opened header-class="bg-gray-200 dark:bg-gray-900 text-lg font-bold text-blue-900 dark:text-blue-100"'):
                ui.number("Aktuelles Alter", min=18, max=80).bind_value(state, 'current_age').classes('w-full mb-1')
                ui.number("Frührente (Alter)", min=50, max=67).bind_value(state, 'early_retirement_age').classes('w-full mb-1')
                ui.number("Endalter (Lebenserwartung)", min=70, max=120).bind_value(state, 'end_age').classes('w-full mb-1')
                ui.input("Aktuelles Bruttogehalt (€/Jahr)").bind_value(state, 'salary', forward=parse_money, backward=format_money).props('mask="#.###.###" reverse-fill-mask unmasked-value').classes('w-full mb-1')
                ui.checkbox("In Altersteilzeit arbeiten?").bind_value(state, 'do_partial_retirement').classes('w-full dark:text-white')
                with ui.column().bind_visibility_from(state, 'do_partial_retirement').classes('w-full pl-4 border-l-2 border-blue-200 dark:border-blue-800 mb-1'):
                    ui.number("Dauer (Jahre)", min=1, step=1).bind_value(state, 'partial_duration').classes('w-full mb-1')
                    ui.input("Gehalt in Teilzeit (€/Jahr)").bind_value(state, 'partial_salary', forward=parse_money, backward=format_money).props('mask="#.###.###" reverse-fill-mask unmasked-value').classes('w-full mb-1')
                ui.input("Ziel-Netto im Ruhestand (€/Monat)").bind_value(state, 'target_net', forward=parse_money, backward=format_money).props('mask="#.###.###" reverse-fill-mask unmasked-value').classes('w-full')

            with ui.expansion('2. Wirtschaftliche Annahmen', icon='trending_up').classes('w-full bg-gray-100 dark:bg-gray-800 shadow-md rounded-md text-black dark:text-white').props('default-opened header-class="bg-gray-200 dark:bg-gray-900 text-lg font-bold text-blue-900 dark:text-blue-100"'):
                ui.number("Inflationsrate (%)", step=0.1).bind_value(state, 'inflation').classes('w-full mb-1')
                ui.number("Rendite vor Rente (%)", step=0.1).bind_value(state, 'return_pre').classes('w-full mb-1')
                ui.number("Rendite im Ruhestand (%)", step=0.1).bind_value(state, 'return_post').classes('w-full mb-1')
                ui.number("Basiszins Vorabpauschale 2026 (%)", step=0.1).bind_value(state, 'basiszinssatz').classes('w-full')

            with ui.expansion('3. Aktienmarkt (Depot)', icon='show_chart').classes('w-full bg-gray-100 dark:bg-gray-800 shadow-md rounded-md text-black dark:text-white').props('default-opened header-class="bg-gray-200 dark:bg-gray-900 text-lg font-bold text-blue-900 dark:text-blue-100"'):
                ui.input("Aktueller Depotbestand (€)").bind_value(state, 'stock_initial', forward=parse_money, backward=format_money).props('mask="#.###.###" reverse-fill-mask unmasked-value').classes('w-full mb-1')
                ui.input("Monatliche Sparrate (€)").bind_value(state, 'stock_monthly', forward=parse_money, backward=format_money).props('mask="#.###.###" reverse-fill-mask unmasked-value').classes('w-full mb-1')
                ui.number("Anzahl ETF-Wechsel", min=0, max=10, step=1).bind_value(state, 'etf_switches').classes('w-full mb-1')
                ui.label("LIFO-Strategie: Im Ruhestand wird der jüngste ETF zuerst verkauft.").classes('text-xs text-gray-500 dark:text-gray-400 italic')

            with ui.expansion('4. Private Rente (Schicht 3)', icon='savings').classes('w-full bg-gray-100 dark:bg-gray-800 shadow-md rounded-md text-black dark:text-white').props('default-opened header-class="bg-gray-200 dark:bg-gray-900 text-lg font-bold text-blue-900 dark:text-blue-100"'):
                ui.input("Aktuelles Rentenguthaben (€)").bind_value(state, 'priv_initial', forward=parse_money, backward=format_money).props('mask="#.###.###" reverse-fill-mask unmasked-value').classes('w-full mb-1')
                ui.input("Monatlicher Beitrag (€)").bind_value(state, 'priv_monthly', forward=parse_money, backward=format_money).props('mask="#.###.###" reverse-fill-mask unmasked-value').classes('w-full mb-1')
                ui.number("Gebühr Einzahlungen (%)", step=0.10).bind_value(state, 'priv_fee_contrib').classes('w-full mb-1')
                ui.number("Jährliche Gebühr Bestand (%)", step=0.01).bind_value(state, 'priv_fee_balance').classes('w-full')

            with ui.expansion('5. Gesetzliche Rente', icon='account_balance').classes('w-full bg-gray-100 dark:bg-gray-800 shadow-md rounded-md text-black dark:text-white').props('default-opened header-class="bg-gray-200 dark:bg-gray-900 text-lg font-bold text-blue-900 dark:text-blue-100"'):
                ui.number("Aktuelle Rentenpunkte (EP)", step=1.0).bind_value(state, 'current_ep').classes('w-full')

            with ui.expansion('6. Krankenversicherung', icon='local_hospital').classes('w-full bg-gray-100 dark:bg-gray-800 shadow-md rounded-md text-black dark:text-white').props('default-opened header-class="bg-gray-200 dark:bg-gray-900 text-lg font-bold text-blue-900 dark:text-blue-100"'):
                ui.select(["KVdR", "Freiwillig"], label="GKV-Status").bind_value(state, 'gkv_status_display').classes('w-full mb-1')
                ui.number("GKV-Beitragssatz + Zusatz (%)", step=0.1).bind_value(state, 'kv_rate').classes('w-full mb-1')
                ui.number("PV-Beitragssatz (%)", step=0.1).bind_value(state, 'pv_rate').classes('w-full')

        def run_simulation():
            results_container.clear()
            
            final_retirement_age = state.early_retirement_age
            if state.early_retirement_age < 67 and state.do_partial_retirement:
                final_retirement_age = state.early_retirement_age + state.partial_duration
                
            params = {
                'current_age': int(state.current_age), 'end_age': int(state.end_age), 'early_retirement_age': int(state.early_retirement_age), 
                'salary': float(state.salary), 'partial_salary': float(state.partial_salary), 'target_net_income': float(state.target_net),
                'do_partial_ret': bool(state.do_partial_retirement), 'final_ret_age': int(final_retirement_age),
                'inflation': float(state.inflation), 'return_pre': float(state.return_pre), 'return_post': float(state.return_post), 'basiszinssatz': float(state.basiszinssatz),
                'stock_initial': float(state.stock_initial), 'stock_monthly': float(state.stock_monthly), 'etf_switches': int(state.etf_switches),
                'priv_initial': float(state.priv_initial), 'priv_monthly': float(state.priv_monthly),
                'priv_fee_contrib': float(state.priv_fee_contrib), 'priv_fee_balance': float(state.priv_fee_balance),
                'current_ep': float(state.current_ep),
                'gkv_status': state.gkv_status_display, 
                'kv_rate': float(state.kv_rate), 'pv_rate': float(state.pv_rate)
            }
            
            with results_container:
                ui.label("Ergebnisse werden berechnet...").classes('text-lg text-gray-500 dark:text-gray-400 italic')
            
            # Calculate
            try:
                df = simulate_wealth(params)
                stock_flat, priv_flat = calculate_flat_savings_equivalent(params)
                
                # UI updates
                results_container.clear()
                with results_container:
                    ui.markdown(f"**💡 Info zur Inflationsanpassung:** Die Simulation geht davon aus, dass Sie Ihre monatlichen Sparraten jährlich um die Inflation ({state.inflation}%) erhöhen. Möchten Sie Ihre Sparrate stattdessen konstant halten, müssten Sie von Beginn an **{stock_flat:,.0f} € ins Depot** und **{priv_flat:,.0f} € in die private Rente** sparen, um exakt dasselbe nominale Endkapital zu Rentenbeginn zu erreichen.").classes('bg-blue-50 dark:bg-blue-900 p-4 rounded-lg shadow-inner text-blue-900 dark:text-blue-200 border border-blue-200 dark:border-blue-800 mb-6')
                    
                    # Translate dataframe columns
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
                    
                    ui.label("Vermögensentwicklung & Entnahme (Kaufkraftbereinigt)").classes('text-2xl font-bold mt-8')
                    ui.label("Dieses Diagramm zeigt Ihr inflationsbereinigtes Kapital und stellt die tatsächliche heutige Kaufkraft Ihres Geldes dar.").classes('text-gray-600 dark:text-gray-400 mb-4')
                    
                    df_plot = df[['Alter', 'Realer Depotbestand', 'Reales privates Rentenguthaben']].copy()
                    
                    chart_font = dict(family='"Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "Helvetica Neue", "Arial", sans-serif', size=14, color='gray')
                    title_font = dict(family='"Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "Helvetica Neue", "Arial", sans-serif', size=22, color='gray')
                    
                    fig1 = px.area(df_plot, x='Alter', y=['Reales privates Rentenguthaben', 'Realer Depotbestand'], 
                                  title="<b>Kapitalprojektion (Kaufkraftbereinigt)</b>",
                                  labels={'value': '<b>Vermögen (€)</b>', 'variable': '<b>Säule</b>', 'Alter': '<b>Alter</b>'},
                                  color_discrete_sequence=['#1f77b4', '#2ca02c'])
                    
                    fig1.add_vline(x=state.early_retirement_age, line_dash="dash", line_color="purple", annotation_text=f"Alter {state.early_retirement_age} (Ende Vollzeit)", annotation_position="top left")
                    if state.early_retirement_age < 67 and state.do_partial_retirement:
                         fig1.add_vline(x=final_retirement_age, line_dash="dash", line_color="magenta", annotation_text=f"Alter {final_retirement_age} (Ende Teilzeit)", annotation_position="top right")
                    fig1.add_vline(x=62, line_dash="dash", line_color="red", annotation_text="Alter 62 (Priv. Auszahlung)", annotation_position="bottom left")
                    fig1.add_vline(x=67, line_dash="dash", line_color="orange", annotation_text="Alter 67 (Gesetzl. Rente)", annotation_position="bottom right")
                    fig1.update_layout(margin=dict(l=20, r=20, t=60, b=140), legend=dict(orientation="h", yanchor="top", y=-0.35, xanchor="center", x=0.5), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=chart_font, title_font=title_font)
                    fig1.update_xaxes(showgrid=True, gridwidth=1.2, gridcolor='rgba(128, 128, 128, 0.2)')
                    fig1.update_yaxes(showgrid=True, gridwidth=1.2, gridcolor='rgba(128, 128, 128, 0.2)')
                    ui.plotly(fig1).classes('w-full h-[460px]')
                    
                    ui.label("Einkommensströme im Ruhestand (Brutto, Kaufkraftbereinigt)").classes('text-2xl font-bold mt-8')
                    ui.label("Dieses Diagramm zeigt die Zusammensetzung Ihrer monatlichen Entnahmen und Renten (Durchschnitt pro Jahr) ab Beginn der Auszahlungsphase in heutiger Kaufkraft.").classes('text-gray-600 dark:text-gray-400 mb-4')
                    
                    df_payout = df[df['Alter'] > state.early_retirement_age].copy()
                    df_payout['Alter'] -= 1
                    df_payout['Reale Gesetzliche Rente (Brutto)'] /= 12
                    df_payout['Reale Private Auszahlung (Brutto)'] /= 12
                    df_payout['Gehalt Altersteilzeit (Brutto)'] /= 12
                    df_payout['Reale Depotentnahme (Brutto)'] /= 12
                    
                    fig2 = px.bar(df_payout, x='Alter', y=['Reale Gesetzliche Rente (Brutto)', 'Reale Private Auszahlung (Brutto)', 'Gehalt Altersteilzeit (Brutto)', 'Reale Depotentnahme (Brutto)'],
                                        title="<b>Monatliche Gesamtauszahlung (Kaufkraftbereinigt)</b>",
                                        labels={'value': '<b>Auszahlung (€/Monat)</b>', 'variable': '<b>Einkommensquelle</b>', 'Alter': '<b>Alter</b>'},
                                        color_discrete_sequence=['#ff7f0e', '#1f77b4', '#8c564b', '#2ca02c'])
                    fig2.update_layout(margin=dict(l=20, r=20, t=60, b=140), legend=dict(orientation="h", yanchor="top", y=-0.35, xanchor="center", x=0.5), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=chart_font, title_font=title_font)
                    fig2.update_xaxes(showgrid=True, gridwidth=1.2, gridcolor='rgba(128, 128, 128, 0.2)')
                    fig2.update_yaxes(showgrid=True, gridwidth=1.2, gridcolor='rgba(128, 128, 128, 0.2)')
                    ui.plotly(fig2).classes('w-full h-[460px]')
        
                    ui.label("Steuern & Abgaben im Ruhestand (Kaufkraftbereinigt)").classes('text-2xl font-bold mt-8')
                    ui.label("Dieses Diagramm zeigt Ihre monatlichen Steuer- und Krankenkassenbelastungen (Durchschnitt pro Jahr) ab Beginn der Auszahlungsphase in heutiger Kaufkraft.").classes('text-gray-600 dark:text-gray-400 mb-4')
                    
                    df_taxes = df[df['Alter'] > state.early_retirement_age].copy()
                    df_taxes['Alter'] -= 1
                    df_taxes['Steuer auf ges. Rente'] /= 12
                    df_taxes['Steuer auf priv. Rente'] /= 12
                    df_taxes['Steuer auf Gehalt'] /= 12
                    df_taxes['Steuer auf Depotentnahme'] /= 12
                    df_taxes['Vorabpauschale (Depot)'] /= 12
                    df_taxes['GKV & PV Beiträge'] /= 12
                    
                    fig3 = px.bar(df_taxes, x='Alter', y=['Steuer auf ges. Rente', 'Steuer auf priv. Rente', 'Steuer auf Gehalt', 'Steuer auf Depotentnahme', 'Vorabpauschale (Depot)', 'GKV & PV Beiträge'],
                                        title="<b>Monatliche Steuern & Abgaben (Kaufkraftbereinigt)</b>",
                                        labels={'value': '<b>Abgaben (€/Monat)</b>', 'variable': '<b>Abgabenart</b>', 'Alter': '<b>Alter</b>'},
                                        color_discrete_sequence=['#d62728', '#9467bd', '#1f77b4', '#8c564b', '#17becf', '#e377c2'])
                    fig3.update_layout(margin=dict(l=20, r=20, t=60, b=140), legend=dict(orientation="h", yanchor="top", y=-0.35, xanchor="center", x=0.5), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=chart_font, title_font=title_font)
                    fig3.update_xaxes(showgrid=True, gridwidth=1.2, gridcolor='rgba(128, 128, 128, 0.2)')
                    fig3.update_yaxes(showgrid=True, gridwidth=1.2, gridcolor='rgba(128, 128, 128, 0.2)')
                    ui.plotly(fig3).classes('w-full h-[460px]')
                    
                    ui.label("Detaillierte jährliche Projektion").classes('text-2xl font-bold mt-8 mb-4')
                    
                    # format df for display
                    df_display = df.round(0).copy()
                    
                    column_defs = [{'field': col, 'headerName': col, 'sortable': True, 'filter': True} for col in df_display.columns]
                    ui.aggrid({
                        'columnDefs': column_defs,
                        'rowData': df_display.to_dict('records')
                    }).classes('w-full h-96')
                    
                # Optional: Auto-scroll to results after calculation
                ui.run_javascript(f'document.getElementById("c{results_container.id}").scrollIntoView({{behavior: "smooth"}})')
        
            except Exception as e:
                results_container.clear()
                with results_container:
                    ui.label(f"Fehler bei der Berechnung: {str(e)}").classes('text-red-500 dark:text-red-400 font-bold p-4')

        ui.button("🚀 Simulation starten", on_click=run_simulation, color='primary').classes('w-full mt-6 py-4 text-xl font-bold shadow-lg')

        results_container = ui.column().classes('w-full mt-4')

        with ui.expansion('⚠️ Disclaimer (Haftungsausschluss)', icon='warning').classes('w-full bg-yellow-50 dark:bg-yellow-900 border border-yellow-200 dark:border-yellow-800 mt-8 text-black dark:text-white').props('header-class="text-lg font-bold"'):
            ui.markdown("""
            Dieses Tool dient ausschließlich zu Informations- und Bildungszwecken. Es stellt keine Finanz-, Steuer- oder Rechtsberatung dar. 
            Die Berechnungen basieren auf den gesetzlichen Regelungen und Parametern des Jahres 2026, welche sich in Zukunft jederzeit ändern können. 
            Alle Ergebnisse sind stark vereinfachte Modellrechnungen und Schätzungen. Für die tatsächliche Richtigkeit, Vollständigkeit und Anwendbarkeit der Berechnungen auf Ihre persönliche Situation wird keine Gewähr übernommen.
            Bitte konsultieren Sie für verlässliche Planungen einen qualifizierten Steuerberater oder Finanzexperten.
            """)
            
        with ui.expansion('ℹ️ INFO: Berechnungs- und Steuerdetails anzeigen', icon='info').classes('w-full !bg-gray-100 dark:!bg-gray-800 shadow-md rounded-md text-black dark:text-white mb-6').props('header-class="!bg-gray-200 dark:!bg-gray-900 text-lg font-bold text-blue-900 dark:!text-blue-100"'):
            with ui.column().classes('w-full gap-4 p-4 !bg-transparent'):
                with ui.card().classes('w-full shadow-sm !bg-gray-50 dark:!bg-gray-800 !text-black dark:!text-white'):
                    ui.label('💡 Allgemeine Berechnungsgrundlage (Inflation)').classes('text-lg font-bold text-blue-800 dark:text-blue-300 border-b pb-2 w-full')
                    ui.markdown('Alle internen Berechnungen des Tools finden in **nominalen Werten** statt (also unter Einbeziehung der Inflation über die Jahre). Um Ihnen jedoch ein intuitives Verständnis zu geben, werden alle ausgegebenen Zahlen (Vermögen, Steuern, Entnahmen) in die **heutige Kaufkraft (real)** zurückgerechnet.').classes('!text-black dark:!text-gray-100')

                with ui.card().classes('w-full shadow-sm !bg-gray-50 dark:!bg-gray-800 !text-black dark:!text-white'):
                    ui.label('1. Gesetzliche Rente (GRV)').classes('text-lg font-bold text-blue-800 dark:text-blue-300 border-b pb-2 w-full')
                    ui.markdown('''Die gesetzliche Rente wird durch das Sammeln von **Rentenpunkten (Entgeltpunkten, EP)** simuliert.\n\n* **Ansparphase:** Während Sie arbeiten, wird Ihr Bruttogehalt durch das Durchschnittsentgelt (ca. 51.944 € für 2026) geteilt, um Ihre jährlichen Rentenpunkte zu ermitteln. Das maximal anrechenbare Gehalt ist durch die Beitragsbemessungsgrenze (101.400 €) gedeckelt. Altersteilzeit wird ebenfalls unterstützt und bringt proportionale Punkte.\n\n* **Auszahlungsphase (ab 67):** Jeder gesammelte Rentenpunkt ist monatlich 42,52 € wert (Rentenwert 2026).''').classes('!text-black dark:!text-gray-100')

                with ui.card().classes('w-full shadow-sm !bg-gray-50 dark:!bg-gray-800 !text-black dark:!text-white'):
                    ui.label('2. Private Rentenversicherung').classes('text-lg font-bold text-blue-800 dark:text-blue-300 border-b pb-2 w-full')
                    ui.markdown('''Die private Rente ist in drei Phasen unterteilt und nutzt steuerlich das attraktive **Halbeinkünfteverfahren (12/62-Regel)**:\n\n* **Phase 1 (Bis Alter 50):** Sie zahlen monatlich ein. Nach Abzug einer Abschlussgebühr (z.B. 0,50%) wächst Ihr Geld am Kapitalmarkt, abzüglich einer laufenden Verwaltungsgebühr (z.B. 0,22%).\n\n* **Phase 2 (Alter 50 bis 62):** Die Einzahlungen stoppen, aber das Kapital wächst weiter.\n\n* **Phase 3 (Alter 62 bis 85):** Das Kapital wird als lebenslange Rente (bzw. bis Alter 85) ausgezahlt.\n\n* **Besteuerung (12/62-Regel):** Da der Vertrag über 12 Jahre lief und erst ab Alter 62 ausgezahlt wird, ist nur der **Gewinn** steuerpflichtig. Der Gewinn ist definiert als die **Bruttoauszahlung minus dem proportionalen Anteil der ursprünglichen Einzahlungen**. Von diesem Gewinn sind nochmal 15% pauschal steuerfrei (Teilfreistellung). Die verbleibende Summe müssen Sie nur **zur Hälfte (50%)** mit Ihrem persönlichen Einkommensteuersatz versteuern.''')

                with ui.card().classes('w-full shadow-sm !bg-gray-50 dark:!bg-gray-800 !text-black dark:!text-white'):
                    ui.label('3. Aktienmarkt (Depot) & Vorabpauschale').classes('text-lg font-bold text-blue-800 dark:text-blue-300 border-b pb-2 w-full')
                    ui.markdown('''Das Depot wird präzise nach dem **FIFO-Prinzip (First-In, First-Out)** und mit den Regeln für die **Vorabpauschale** berechnet.\n\n* **Vorabpauschale:** Diese "Vorab-Steuer" wird jährlich auf fiktive Erträge Ihres Depots berechnet (Basiszins 2026: 3,20%). Für Aktien-ETFs sind 30% steuerfrei. Die Steuer wird erst mit Ihrem Sparerpauschbetrag (1.000 €) verrechnet, bevor die tatsächliche Abgeltungsteuer (26,375%) greift. Gezahlte Vorabpauschalen werden beim späteren Verkauf steuermindernd angerechnet.\n\n* **Entnahme im Ruhestand:** Das Tool berechnet automatisch, wie viel Sie aus dem Depot entnehmen müssen, um Ihre gewünschte Nettolücke zu schließen. Da die zu zahlenden Steuern und Krankenkassenbeiträge von der Höhe der Bruttoentnahme abhängen, nutzt das Tool im Hintergrund einen **binären Suchalgorithmus**, um exakt den Bruttobetrag zu finden, der nach allen Abzügen genau Ihr Nettoziel trifft. Nur der Gewinnanteil der verkauften Anteile wird besteuert (wiederum abzüglich 30% Teilfreistellung).\n\n* **Tipp (ETF-Wechsel):** Um Steuern im Ruhestand zu optimieren, können Sie in der Ansparphase den besparten ETF in regelmäßigen Abständen wechseln. Im Ruhestand verkaufen Sie dann die jüngsten Anteile zuerst (LIFO-Strategie), was die Steuerlast deutlich senkt.''')

                with ui.card().classes('w-full shadow-sm !bg-gray-50 dark:!bg-gray-800 !text-black dark:!text-white'):
                    ui.label('4. Kranken- und Pflegeversicherung (GKV/PV)').classes('text-lg font-bold text-blue-800 dark:text-blue-300 border-b pb-2 w-full')
                    ui.markdown('''Die Krankenversicherung kann im Ruhestand einer der größten Kostenfaktoren sein.\n\n* **Angestelltenphase:** Während Sie arbeiten, wird zur Ermittlung der Steuerbasis pauschal ein **Abzug von 10%** vom Bruttogehalt für die Sozialabgaben angenommen.\n\n* **Privatier (Frührente vor Alter 67):** Wenn Sie nicht arbeiten, sind Sie "freiwillig gesetzlich versichert". Sie müssen auf **Ihr gesamtes Einkommen** (Depotgewinne, private Rente) volle Kranken- und Pflegebeiträge zahlen (bis zur Bemessungsgrenze von ca. 69.750 €/Jahr). Das Mindesteinkommen beträgt 14.140 €/Jahr.\n\n* **Gesetzliche Rente (ab Alter 67):**\n    * **KVdR (Krankenversicherung der Rentner):** Wenn Sie die Voraussetzungen erfüllen, zahlen Sie GKV-Beiträge **nur auf Ihre gesetzliche Rente** (und nur den halben Beitragssatz für die KV!). Depot und private Rente sind in der Krankenversicherung komplett **abgabenfrei**.\n    * **Freiwillig versichert:** Erfüllen Sie die KVdR nicht, zahlen Sie auch im gesetzlichen Rentenalter auf **alle** Einkunftsarten den vollen Beitragssatz.''')

                with ui.card().classes('w-full shadow-sm !bg-gray-50 dark:!bg-gray-800 !text-black dark:!text-white'):
                    ui.label('5. Einkommensteuer (ESt)').classes('text-lg font-bold text-blue-800 dark:text-blue-300 border-b pb-2 w-full')
                    ui.markdown('''Das Tool nutzt den voraussichtlichen **Einkommensteuertarif 2026**. Die Steuerlast wird nach folgenden Progressionszonen berechnet:\n\n* **Zone 1 (Grundfreibetrag):** 0 € bis 12.336 € (Steuerfrei)\n\n* **Zone 2:** Bis 17.005 € (Eingangssteuersatz)\n\n* **Zone 3:** Bis 66.760 € (Hauptprogressionszone)\n\n* **Zone 4:** Bis 277.825 € (Spitzensteuersatz von pauschal 42%)\n\n* **Zone 5:** Ab 277.826 € (Reichensteuer von pauschal 45%)\n\nDie Gesamtsteuerlast auf alle Ihre Einkünfte wird in nominalen Werten berechnet und im Tool proportional auf Ihre Einkommensquellen aufgeteilt, um Ihnen ein exaktes Bild Ihrer Nettobelastung zu zeigen.''')

    ui.markdown("<div style='text-align: center; color: gray; margin-top: 40px; margin-bottom: 40px;'><small>Bei Fragen oder Anregungen kontaktieren Sie mich gerne unter: <a href='mailto:ericguenl@gmail.com'>ericguenl@gmail.com</a> | <a href='https://github.com/Chocho74/Wealth_tracker' target='_blank'>Projekt auf GitHub ansehen</a></small></div>")

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="Deutscher Rentenplaner", favicon="📈", host="0.0.0.0", port=7860, reload=False)