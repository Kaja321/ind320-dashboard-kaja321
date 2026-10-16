# Side 3: Kraftutveksling mellom Norge og nabolandene (data fra ENTSO-E, lagret i MongoDB).
# Venstre kolonne: velg forbindelse (st.radio) og år (st.selectbox), og se et sektordiagram.
# Høyre kolonne: velg måneder (st.pills) og se et linjeplott.

import pandas as pd
import plotly.express as px
import pymongo
import streamlit as st

st.set_page_config(layout="wide")
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

    # groupby sorterer alfabetisk (export før import), så navnene står i samme rekkefølge
    fig_pie = px.pie(
        values=totals.values,
        names=["Out of Norway (export)", "Into Norway (import)"],
        title=f"Power exchange in {year} (TWh)<br>{connection_names[connection]}",
    )
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
        # Én linje for hver retning
        fig_line = px.line(
            df_months,
            x="time",
            y="flow_mw",
            color="direction",
            title=f"Hourly power flow {connection_names[connection]} in {year}",
            labels={"time": "Time (UTC)", "flow_mw": "Power flow (MW)", "direction": "Direction"},
        )
        st.plotly_chart(fig_line, width="stretch")

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