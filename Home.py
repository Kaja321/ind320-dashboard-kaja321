# Forside (hovedside) for IND320-appen.
# Streamlit lager automatisk en meny i sidebaren med alle filene i pages/-mappa,
# slik at brukeren kan navigere mellom sidene herfra.
 
import pandas as pd
import streamlit as st
 
# Setter tittel i nettleserfanen og bred layout (samme som de andre sidene)
st.set_page_config(page_title="IND320 Dashboard", layout="wide")
 
 
# Leser inn data med caching, slik at nøkkeltallene under ikke leser fila på nytt hver gang
@st.cache_data
def load_data():
    df = pd.read_csv("reservoirs.csv")
    df["dato_Id"] = pd.to_datetime(df["dato_Id"])
    return df
 
 
df = load_data()
 
# Velger strømprisområde NO1 (omrType "EL" OG omrnr 1) og sorterer etter dato
df_no1 = df[(df["omrType"] == "EL") & (df["omrnr"] == 1)].sort_values("dato_Id")
 
# Henter den siste målingen, som brukes i nøkkeltallene
latest = df_no1.iloc[-1]
 
# ---------- Overskrift og introduksjon ----------
st.title("Norwegian Hydropower Reservoirs")
st.write(
    "Most of Norway's electricity comes from hydropower. Water is stored in "
    "reservoirs and used to produce electricity when it is needed. This dashboard "
    "explores how full the reservoirs have been every week since 1995."
)
 
# ---------- Nøkkeltall ----------
# st.metric viser et tall stort og tydelig. delta viser endringen fra forrige uke.
st.subheader(f"Latest measurement for NO1 ({latest['dato_Id'].strftime('%d %B %Y')})")
 
col1, col2, col3 = st.columns(3)   # deler siden i tre kolonner ved siden av hverandre
col1.metric(
    "Fill level",
    f"{latest['fyllingsgrad']:.0%}",
    f"{latest['endring_fyllingsgrad']:+.1%} from last week",
)
col2.metric("Stored energy", f"{latest['fylling_TWh']:.2f} TWh")
col3.metric("Capacity", f"{latest['kapasitet_TWh']:.2f} TWh")
 
# ---------- Oversikt over sidene ----------
st.subheader("What you can explore")
st.markdown(
    """
- **Table** – an overview of every column in the dataset, with mini charts for the first month
- **Plot** – interactive plots where you choose variables and time period
- **Test** – a test page for further development
"""
)
 
# ---------- Om dataene ----------
st.subheader("About the data")
st.write(
    "The data contains weekly reservoir statistics for several areas in Norway. "
    "This app focuses on price area NO1 (Eastern Norway). The data is read from "
    "a local CSV file, and will later be replaced by a MongoDB database."
)
 
# Kort hjelpetekst i sidebaren, over menyen Streamlit lager automatisk
st.sidebar.info("Use the menu above to navigate between the pages.")