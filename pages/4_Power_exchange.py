# Side i Overview-gruppen: kraftutveksling mellom Norge og nabolandene (data fra ENTSO-E, lagret i MongoDB).
# Venstre kolonne: velg forbindelse (st.radio) og år (st.selectbox), og se et sektordiagram.
# Høyre kolonne: velg måneder (st.pills) og se et linjeplott.
import pandas as pd
import plotly.express as px
import pymongo
import streamlit as st
from functions import COLORS   # Felles farger for hele appen
import plotly.graph_objects as go

st.title("Power Exchange with Neighbouring Countries")

# Kobler til MongoDB med adressen fra secrets.toml (samme som i lærerens eksempel).
# st.cache_resource gjør at koblingen bare lages én gang.
@st.cache_resource
def init_connection():
    return pymongo.MongoClient(st.secrets["mongo"]["uri"])

client = init_connection()

# Henter alle dokumentene fra samlingen "flows" og gjør dem om til en tabell.
# st.cache_data gjør at dataene bare lastes ned én gang.
@st.cache_data
def get_data():
    collection = client["ind320"]["flows"]
    items = list(collection.find({}, {"_id": 0}))   # {"_id": 0} tar bort MongoDB sin id-kolonne
    df = pd.DataFrame(items)
    df["time"] = pd.to_datetime(df["time"])
    return df

df = get_data()
month_names = ["January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]
# Lesbare navn på forbindelsene, som vises ved radioknappene i stedet for kodene
connection_names = {
    "NO_1-SE_3": "NO1 – Sweden (SE3)",
    "NO_2-DE_LU": "NO2 – Germany (NordLink)",
    "NO_2-DK_1": "NO2 – Denmark (Skagerrak)",
    "NO_2-GB": "NO2 – Great Britain (North Sea Link)",
    "NO_2-NL": "NO2 – Netherlands (NorNed)",
    "NO_3-SE_2": "NO3 – Sweden (SE2)",
    "NO_4-FI": "NO4 – Finland",
    "NO_4-SE_1": "NO4 – Sweden (SE1)",
    "NO_4-SE_2": "NO4 – Sweden (SE2)",
}
# Deler siden i to kolonner med ramme rundt, slik som i lærerens eksempel
left, right = st.columns(2, border=True)
# ---------- Venstre kolonne: sektordiagram ----------
with left:
    # st.radio: velger forbindelse. format_func viser de lesbare navnene i stedet for kodene.
    connection = st.radio("Select connection:", sorted(df["connection"].unique()),
                          format_func=connection_names.get)
    # Forklarer de norske områdekodene under radioknappene
    st.caption("NO1 = South-East, NO2 = South-West, NO3 = Central, NO4 = Northern Norway")
    # st.selectbox: velger år. index=1 gjør at 2025 (det første hele året) er valgt fra start.
    year = st.selectbox("Select year:", sorted(df["time"].dt.year.unique()), index=1)
    # Plukker ut radene for valgt forbindelse og år
    df_year = df[(df["connection"] == connection) & (df["time"].dt.year == year)]
    # Summerer timesverdiene per retning (MW per time = MWh) og gjør om til TWh
    totals = df_year.groupby("direction")["flow_mw"].sum() / 1_000_000
    
    # Faste navn og farger for hver retning, så eksport alltid er blå og import alltid oransje
    direction_names = {"export": "Out of Norway (export)", "import": "Into Norway (import)"}
    direction_colors = {"Out of Norway (export)": COLORS[0], "Into Norway (import)": COLORS[1]}
    names = totals.index.map(direction_names)   # bruker indeksen, så navn og verdier alltid hører sammen
    fig_pie = px.pie(
        values=totals.values,
        names=names,
        color=names,
        color_discrete_map=direction_colors,
        title=f"Power exchange in {year} (TWh)<br>{connection_names[connection]}",
    )
    # Beholder samme rekkefølge (eksport, import) i stedet for å sortere etter størrelse,
    # så forklaringen og bitene står likt for alle forbindelser
    fig_pie.update_traces(sort=False)
    
    st.plotly_chart(fig_pie, width="stretch")
# ---------- Høyre kolonne: linjeplott ----------
with right:
    # st.pills: velger én eller flere måneder
    selected_months = st.pills("Select months:", month_names,
                               selection_mode="multi", default=["January"])
    # Gjør om månedsnavn til tall (January = 1, February = 2, ...)
    month_numbers = [month_names.index(m) + 1 for m in selected_months]
    # Plukker ut valgte måneder og sorterer etter tid
    df_months = df_year[df_year["time"].dt.month.isin(month_numbers)].sort_values("time")
    if df_months.empty:
        st.info("No data for the selected months. The data covers October 2024 to October 2026.")
    else:
                # Nettoflyt per time: eksport minus import. Strømmen går bare én vei om gangen,
        # så én kurve er lettere å lese enn to linjer som hele tiden hopper ned til null.
        # pivot_table gir én kolonne per retning, og fill_value=0 fyller timer uten verdi.
        flows = df_months.pivot_table(index="time", columns="direction",
                                      values="flow_mw", fill_value=0)
        net = flows.get("export", 0) - flows.get("import", 0)

        # Positiv nettoflyt (eksport) fylles blått over null, negativ (import) oransje under null
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(x=net.index, y=net.clip(lower=0), mode="lines", fill="tozeroy",
                                      name="Out of Norway (export)",
                                      line=dict(color=COLORS[0], width=0.8)))
        fig_line.add_trace(go.Scatter(x=net.index, y=net.clip(upper=0), mode="lines", fill="tozeroy",
                                      name="Into Norway (import)",
                                      line=dict(color=COLORS[1], width=0.8)))
        fig_line.update_layout(
            title=f"Net hourly power flow {connection_names[connection]} in {year}",
            xaxis_title="Time (UTC)",
            yaxis_title="Net export (MW)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified",   # én samlet boks med tid og verdi når man holder musa over
        )
        st.plotly_chart(fig_line, width="stretch")

        st.caption("Positive values: power flows out of Norway (export). "
                   "Negative values: power flows into Norway (import). "
                   "Flat tops show that the connection is running at full capacity.")
        
# ---------- Kilde til dataene ----------
with st.expander("About the data"):
    st.write(
        "The data shows physical cross-border power flows between Norway and neighbouring "
        "countries, from the ENTSO-E Transparency Platform. The data was fetched with the "
        "ENTSO-E API for the last two years, and the 15-minute values were converted to hourly "
        "averages (MW, which equals MWh per hour). The data was stored in a local Cassandra "
        "database using Spark, the relevant columns were extracted with Spark, and the result "
        "was saved in MongoDB, which this page reads from. The data starts in October 2024, so "
        "2024 and 2026 are not complete years. All times are in UTC."
    )