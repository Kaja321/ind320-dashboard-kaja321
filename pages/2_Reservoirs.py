# Side 2: Magasindata fra NVE sitt API.
# Brukeren velger områdetype (st.radio), variabel (st.selectbox) og periode (st.select_slider).
# Tabellen og plottet viser én linje for hvert områdenummer i valgt områdetype.
import pandas as pd
import plotly.express as px
import requests
import streamlit as st
st.set_page_config(layout="wide")
st.title("Reservoir Data")

# Henter dataene fra NVE sitt API og gir kolonnene engelske navn (samme som i notebooken).
# @st.cache_data gjør at dataene bare lastes ned én gang, ikke ved hvert klikk.
@st.cache_data
def load_data():
    url = "https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk/HentOffentligData"
    df = pd.DataFrame(requests.get(url).json())
    df = df.rename(
        columns={
            "dato_Id": "date",
            "omrType": "area_type",
            "omrnr": "area_number",
            "iso_aar": "year",
            "iso_uke": "week",
            "fyllingsgrad": "fill_level",
            "kapasitet_TWh": "capacity_twh",
            "fylling_TWh": "stored_energy_twh",
            "neste_Publiseringsdato": "next_publication_date",
            "fyllingsgrad_forrige_uke": "previous_week_fill_level",
            "endring_fyllingsgrad": "change_in_fill_level",
        }
    )
    # Datoformat, slik at vi kan sortere og hente ut måneder
    df["date"] = pd.to_datetime(df["date"])
    # Hjelpekolonner: måned (f.eks. "1995-01") til slideren, og områdenavn (f.eks. "EL 1")
    df["month"] = df["date"].dt.to_period("M").astype(str)
    df["area"] = df["area_type"] + " " + df["area_number"].astype(str)
    # APIet gir radene i tilfeldig rekkefølge, så de sorteres etter dato
    return df.sort_values("date")

df = load_data()
# Måleverdiene brukeren kan velge mellom
measurements = ["fill_level", "stored_energy_twh", "capacity_twh",
                "previous_week_fill_level", "change_in_fill_level"]
# ---------- Valg ----------
left, right = st.columns(2)
# st.radio: velger områdetype. EL = strømprisområder, NO = hele landet, VASS = vassdragsområder.
with left:
    area_type = st.radio("Select area type:", ["EL", "NO", "VASS"], horizontal=True)
# st.selectbox: velger hvilken variabel som vises
with right:
    selected_col = st.selectbox("Select variable:", measurements)
# st.select_slider: velger periode (fra og med, til og med). Standard er første måned.
months = df["month"].unique().tolist()
start_month, end_month = st.select_slider(
    "Select period:",
    options=months,
    value=(months[0], months[0]),
)
# NVE sitt API har ingen mulighet for å velge periode, så alle dataene lastes ned én gang
# (og caches). Slideren bestemmer hvilken del av dataene som brukes videre.
df_selected = df[(df["area_type"] == area_type) &
                 (df["month"] >= start_month) & (df["month"] <= end_month)]
# Sorterer etter område og dato, så områdene vises i rekkefølge (EL 1, EL 2, ...)
df_selected = df_selected.sort_values(["area", "date"])
# ---------- Tabell ----------
# Én rad per områdenummer, med en minigraf (LineChartColumn) for valgt variabel og periode
table_rows = []
for area in df_selected["area"].unique():
    values = df_selected[df_selected["area"] == area][selected_col].tolist()
    table_rows.append({"Area": area, selected_col: values})
# Viser tabellen i appen. column_config gjør at kolonnen med verdiene vises som
# små linjegrafer (LineChartColumn) i stedet for som en lang liste med tall.
# hide_index skjuler radnumrene, og width="stretch" gjør at tabellen fyller hele bredden.
st.dataframe(
    pd.DataFrame(table_rows),
    column_config={
        selected_col: st.column_config.LineChartColumn(
            f"{selected_col} ({start_month} to {end_month})", width="large"
        )
    },
    hide_index=True,
    width="stretch",
)
# ---------- Plott ----------
# px.line lager én linje for hvert område (color="area")
fig = px.line(
    df_selected,
    x="date",
    y=selected_col,
    color="area",
    markers=True,
    title=f"{selected_col} for {area_type} areas ({start_month} to {end_month})",
    labels={"date": "Date", selected_col: selected_col, "area": "Area"},
)
st.plotly_chart(fig, width="stretch")
