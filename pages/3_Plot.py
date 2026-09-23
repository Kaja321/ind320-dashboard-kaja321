# Side 3: Interaktivt plott av dataene for strømprisområde NO1.
# Brukeren velger variabel (st.selectbox) og tidsperiode (st.select_slider).
# Standardvalget er første måned i dataserien.
 
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
 
st.title("Interactive Reservoir Data Visualization")
 
 
# Leser inn data fra CSV-fila og gir kolonnene engelske navn.
# @st.cache_data gjør at fila bare leses én gang. Når brukeren endrer et valg,
# kjøres siden på nytt, men dataene hentes fra minnet i stedet for fra fila.
@st.cache_data
def load_data():
    df = pd.read_csv("reservoirs.csv")
 
    # Omdøper kolonnene til engelske og forståelige navn (samme som i notebooken)
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
 
    # Gjør date om til datoformat, slik at vi kan sortere og hente ut måneder
    df["date"] = pd.to_datetime(df["date"])
    return df
 
 
df = load_data()
 
# Velger strømprisområde NO1 (area_type "EL" OG area_number 1) og sorterer etter dato.
# Begge må sjekkes, fordi nummer 1 også brukes av et annet område (VASS 1).
# .copy() lager en egen kopi, slik at vi trygt kan legge til en ny kolonne under.
df_no1 = df[(df["area_type"] == "EL") & (df["area_number"] == 1)].sort_values("date").copy()
 
# Hjelpekolonne med år og måned, for eksempel "1995-01". Brukes av slideren.
df_no1["month"] = df_no1["date"].dt.to_period("M").astype(str)
months = df_no1["month"].unique().tolist()
 
# Alle kolonnene fra CSV-fila som kan velges. date er med på x-aksen, så den er ikke et valg.
csv_columns = [col for col in df_no1.columns if col not in ["date", "month"]]
 
# ---------- Kontroller over plottet ----------
# st.columns deler bredden i to, slik at kontrollene står ved siden av hverandre.
# Slideren får dobbelt så mye plass som nedtrekksmenyen.
left, right = st.columns([1, 2])
 
# st.selectbox: nedtrekksmeny for én kolonne eller alle kolonnene sammen
with left:
    selected_col = st.selectbox("Select column:", ["All columns"] + csv_columns)
 
# st.select_slider: velger en periode (fra og med, til og med).
# Begge endene står på første måned som standard, slik oppgaven krever.
with right:
    start_month, end_month = st.select_slider(
        "Select period:",
        options=months,
        value=(months[0], months[0]),
    )
 
# Plukker ut radene i den valgte perioden.
# Månedene er tekst som "1995-01". Siden året står først, sorteres de riktig som tekst.
df_period = df_no1[(df_no1["month"] >= start_month) & (df_no1["month"] <= end_month)]
 
# ---------- Plottet ----------
# make_subplots med secondary_y gir ett plott med en ekstra y-akse på høyre side
fig = make_subplots(specs=[[{"secondary_y": True}]])
 
if selected_col == "All columns":
    # Alle måleverdiene i samme plott. Variablene har ulike skalaer, så de fordeles
    # på to y-akser (samme løsning som i notebooken):
    # venstre akse for energi (TWh), høyre akse for fyllingsgrad og endring (0–1).
    # year, week og area_number er ikke målinger og tas ikke med.
    for col in ["stored_energy_twh", "capacity_twh"]:
        fig.add_trace(go.Scatter(x=df_period["date"], y=df_period[col], name=col), secondary_y=False)
    for col in ["fill_level", "previous_week_fill_level", "change_in_fill_level"]:
        fig.add_trace(go.Scatter(x=df_period["date"], y=df_period[col], name=col), secondary_y=True)
 
    fig.update_yaxes(title_text="Energy (TWh)", secondary_y=False)
    fig.update_yaxes(title_text="Fraction (0–1)", secondary_y=True)
    title = "All measurement columns"
else:
    # Én valgt kolonne. Punktene viser hver ukentlige måling.
    fig.add_trace(go.Scatter(
        x=df_period["date"],
        y=df_period[selected_col],
        name=selected_col,
        mode="lines+markers",
    ))
    fig.update_yaxes(title_text=selected_col)
    title = selected_col
 
# Felles formatering: tittel med valgt periode, aksetittel og forklaring
fig.update_layout(
    title=f"{title} for NO1 ({start_month} to {end_month})",
    legend_title="Variable",
)
fig.update_xaxes(title_text="Date")
 
# st.plotly_chart viser det interaktive plottet. width="stretch" fyller hele bredden.
st.plotly_chart(fig, width="stretch")