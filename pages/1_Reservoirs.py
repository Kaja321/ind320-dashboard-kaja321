# Side i Overview-gruppen: magasindata fra NVE sitt API.
# Brukeren velger variabel (st.selectbox) og periode (st.select_slider).
# Tabellen og plottet viser én linje for hvert områdenummer i områdetypen som er valgt i sidebaren.
import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from functions import COLORS, area_selector

st.title("Reservoir Data")

# Henter dataene fra NVE sitt API og gir kolonnene engelske navn (samme som i notebooken).
# @st.cache_data gjør at dataene bare lastes ned én gang. ttl=86400 betyr at de
# hentes på nytt etter ett døgn, siden NVE publiserer nye tall hver uke.
@st.cache_data(ttl=86400)
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
    # Fyllingsgraden kommer som andel (0,76). Ganger med 100, så den vises i prosent (76).
    percent_cols = ["fill_level", "previous_week_fill_level", "change_in_fill_level"]
    df[percent_cols] = df[percent_cols] * 100
    # Datoformat, slik at vi kan sortere og hente ut måneder
    df["date"] = pd.to_datetime(df["date"])
    # Hjelpekolonner: måned (f.eks. "1995-01") til slideren, og områdenavn (f.eks. "EL 1")
    df["month"] = df["date"].dt.to_period("M").astype(str)
    df["area"] = df["area_type"] + " " + df["area_number"].astype(str)
    # APIet gir radene i tilfeldig rekkefølge, så de sorteres etter dato
    return df.sort_values("date")

df = load_data()

# Måleverdiene brukeren kan velge mellom, med lesbare navn og enheter.
# Nøkkelen er kolonnenavnet i tabellen, verdien er teksten som vises i appen.
measurements = {
    "fill_level": "Fill level (%)",
    "stored_energy_twh": "Stored energy (TWh)",
    "capacity_twh": "Capacity (TWh)",
    "previous_week_fill_level": "Fill level previous week (%)",
    "change_in_fill_level": "Change from previous week (percentage points)",
}

# ---------- Valg ----------
# Felles områdevalg i sidebaren. Siden viser alle områdene av valgt type,
# så de kan sammenlignes, mens analysesidene bruker det valgte området.
area = area_selector()
area_type = area.split()[0]   # "EL 3" gir "EL"
st.caption(f"Showing all {area_type} areas. Selected area in the sidebar: {area}")

# st.selectbox: velger hvilken variabel som vises.
# Format_func viser det lesbare navnet i stedet for kolonnenavnet.
selected_col = st.selectbox("Select variable:", list(measurements.keys()),
                            format_func=measurements.get)
label = measurements[selected_col]

# st.select_slider: velger periode (fra og med, til og med).
# Standard er de siste 12 månedene, så plottet viser et helt år når siden åpnes.
months = df["month"].unique().tolist()
start_month, end_month = st.select_slider(
    "Select period:",
    options=months,
    value=(months[-12], months[-1]),
)
# NVE sitt API har ingen mulighet for å velge periode, så alle dataene lastes ned én gang
# (og caches). Slideren bestemmer hvilken del av dataene som brukes videre.
df_selected = df[(df["area_type"] == area_type) &
                 (df["month"] >= start_month) & (df["month"] <= end_month)]
# Sorterer etter område og dato, så områdene vises i rekkefølge (EL 1, EL 2, ...)
df_selected = df_selected.sort_values(["area", "date"])

# ---------- Tabell ----------
# Én rad per områdenummer, med en minigraf (LineChartColumn) for valgt variabel og periode.
# Løkkevariabelen heter name, så den ikke overskriver area (valget fra sidebaren).
table_rows = []
for name in df_selected["area"].unique():
    values = df_selected[df_selected["area"] == name][selected_col].tolist()
    table_rows.append({"Area": name, selected_col: values})
# column_config gjør at kolonnen med verdiene vises som små linjegrafer (LineChartColumn)
# i stedet for som en lang liste med tall. hide_index skjuler radnumrene.
st.dataframe(
    pd.DataFrame(table_rows),
    column_config={
        selected_col: st.column_config.LineChartColumn(
            f"{label} ({start_month} to {end_month})", width="large"
        )
    },
    hide_index=True,
    width="stretch",
)

# ---------- Plott ----------
# px.line lager én linje for hvert område (color="area").
# Color_discrete_sequence bruker de felles fargene, så områdene er lette å skille.
fig = px.line(
    df_selected,
    x="date",
    y=selected_col,
    color="area",
    markers=True,
    color_discrete_sequence=COLORS,
    title=f"{label} for {area_type} areas ({start_month} to {end_month})",
    labels={"date": "Date", selected_col: label, "area": "Area"},
)
# Viser én desimal når man holder musa over et punkt
fig.update_yaxes(hoverformat=".1f")
st.plotly_chart(fig, width="stretch")