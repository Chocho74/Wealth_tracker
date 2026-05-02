# Deutscher Rentenplaner (Wealth Tracker)

Ein interaktives Python-Tool (mit Streamlit) zur ganzheitlichen Projektion und Planung der Altersvorsorge in Deutschland. Die Simulation basiert auf den steuerlichen und rechtlichen Rahmenbedingungen für das Jahr 2026.

## 📌 Über das Projekt

Dieses Tool modelliert den langfristigen Vermögensaufbau und die Entnahmephase unter Berücksichtigung der drei wesentlichen Säulen:
1. **Gesetzliche Rente:** Berechnung der Bruttorente basierend auf Entgeltpunkten (EP) und dem aktuellen Rentenwert (2026: 42,52 €/EP).
2. **Private Rentenversicherung (Schicht 3):** Simulation der Anspar-, Ruhe- und Verrentungsphase. Beinhaltet die korrekte steuerliche Behandlung nach dem **Halbeinkünfteverfahren (12/62-Regel)** (nur 50 % des Gewinns nach 15 % Teilfreistellung sind zu versteuern).
3. **Aktiendepot (ETFs):** Projektion des Vermögensaufbaus und der Entnahmen. Berücksichtigt die jährliche **Vorabpauschale** für Aktienfonds (inkl. 30 % Teilfreistellung, Basiszins 3,20 %) sowie die exakte Versteuerung bei Entnahme nach dem **FIFO-Prinzip (First-In, First-Out)**.

Ein besonderer Fokus liegt auf der korrekten Abbildung der **Krankenversicherung im Alter**:
Es wird detailliert zwischen der Krankenversicherung der Rentner (**KVdR**) und der **freiwilligen gesetzlichen Krankenversicherung** (z.B. bei Frührente/Privatiers) unterschieden, was massive Auswirkungen auf die Abgabenlast hat.

Alle ausgegebenen Werte und Grafiken sind **inflationsbereinigt (Kaufkraftbereinigt)**, um ein realistisches Gefühl für den zukünftigen Wert des Geldes zu vermitteln. Die Berechnung im Hintergrund findet jedoch **nominal** statt, um Steuergrenzen und Pauschbeträge korrekt zu berücksichtigen.

## 🚀 Features

*   **Interaktive UI:** Übersichtliche Eingabemasken für persönliche Daten, Annahmen und bestehendes Vermögen via Streamlit.
*   **Akkurate Steuerlogik (2026):**
    *   Einkommensteuertarif 2026 inkl. Beitragsbemessungsgrenzen.
    *   Abgeltungsteuer (25 % + Soli) und Vorabpauschale.
    *   Sparerpauschbetrag (1.000 € pro Person).
*   **GKV / PV Logik:** Exakte Berechnung der Krankenkassenbeiträge bis zur Beitragsbemessungsgrenze, abhängig vom Versichertenstatus.
*   **Teilrente (Partial Retirement):** Möglichkeit, vor dem offiziellen Rentenalter (67) in Teilzeit zu gehen, dabei weiter reduziert Einkommen zu beziehen und anteilige Entgeltpunkte aufzubauen.
*   **ETF-Wechsel (Switches) & FIFO-Optimierung:** Umgehung strikter FIFO-Nachteile durch Simulation von systematischen ETF-Wechseln während der Ansparphase. Dadurch kann in der Entnahmephase steueroptimiert der jüngste ETF zuerst verkauft werden.
*   **Präzise Entnahme-Algorithmen:** Einsatz eines binären Suchalgorithmus (Binary Search) zur exakten Ermittlung der notwendigen Brutto-Aktienentnahme (vor Steuern und GKV), um den gewünschten Netto-Zahlungsstrom zu gewährleisten.
*   **Visuelle Auswertungen:** Generierung von kaufkraftbereinigten Diagrammen (via Plotly) für die Vermögensentwicklung, monatlichen Auszahlungen und Steuerlasten.

## 🛠️ Installation & Ausführung

### Voraussetzungen
*   **Python 3.10.9** (Zwingend erforderlich gem. Projektvorgaben)
*   Empfohlen: Eine virtuelle Umgebung (venv)

### Setup

1. Repository klonen oder herunterladen:
    ```bash
    git clone <repository-url>
    cd Wealth_tracker
    ```

2. Virtuelle Umgebung erstellen und aktivieren (optional, aber empfohlen):
    ```bash
    python -m venv .venv
    # Windows:
    .venv\Scripts\activate
    # macOS/Linux:
    source .venv/bin/activate
    ```

3. Abhängigkeiten installieren:
    ```bash
    pip install -r requirements.txt
    ```
    *(Hinweis: Falls die `requirements.txt` nicht existiert, installieren Sie die benötigten Pakete manuell: `pip install streamlit plotly pandas`)*

### App starten

Starten Sie die Streamlit-App mit folgendem Befehl:

```bash
streamlit run app.py
```

Ihr Standard-Webbrowser öffnet sich daraufhin automatisch unter `http://localhost:8501` mit der Benutzeroberfläche des Rentenplaners.

## 🏗️ Projektstruktur

*   `app.py`: Enthält die Streamlit-Benutzeroberfläche und die Definition der Eingabeparameter sowie die Diagrammerstellung.
*   `calculations.py`: Beinhaltet die gesamte Geschäftslogik, Steueralgorithmen, FIFO-Logik für Depots und die Jahressimulation.
*   `test_calculations.py`: Test-Datei zur Validierung der Berechnungslogik.
*   `GEMINI.md`: Enthält die zugrunde liegenden mathematischen Konstanten und Projekt-Regularien für das Jahr 2026.
*   `WEALTH_PROJECTION_EXPLANATION.md`: Detaillierte Dokumentation zur Berechnungslogik, Steuern und Rentenregeln.

## ⚠️ Disclaimer
Dieses Tool ist ein privates Projekt für Bildungs- und Planungszwecke und stellt **keine Anlage- oder Steuerberatung** dar. Steuergesetze und Sozialabgaben können sich ändern. Die Berechnungen, insbesondere in der Zukunft, basieren auf Annahmen und Schätzungen. Der Code wurde mit AI assistance geschrieben. 