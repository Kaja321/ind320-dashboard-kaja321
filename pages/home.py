# Forsiden i appen: introduksjon, nøkkeltall for NO1 og oversikt over sidene.
# Menyen lages i Home.py med st.navigation.

import pandas as pd
import requests
import streamlit as st


# Henter magasinstatistikken direkte fra NVE sitt API.
# @st.cache_data gjør at dataene bare hentes én gang. ttl=86400 betyr at de
# hentes på nytt etter ett døgn, siden NVE publiserer nye tall hver uke.
@st.cache_data(ttl=86400)
def load_data():
    url = "https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk/HentOffentligData"
    df = pd.DataFrame(requests.get(url).json())
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
    "Most of Norway's electricity comes from hydropower. Water is stored in reservoirs and used "
    "to produce electricity when it is needed. This dashboard explores how full the reservoirs "
    "have been every week since 1995, how the weather affects them, how much power Norway "
    "exchanges with neighbouring countries, and what the fill level may be in the coming months."
)

# ---------- Nøkkeltall ----------
# st.metric viser et tall stort og tydelig. delta viser endringen fra forrige uke.
st.subheader(f"Latest measurement for NO1 ({latest['dato_Id'].strftime('%d %B %Y')})")

col1, col2, col3 = st.columns(3)   # deler siden i tre kolonner ved siden av hverandre
col1.metric(
    "Fill level",
    f"{latest['fyllingsgrad']:.0%}",
    f"{latest['endring_fyllingsgrad'] * 100:+.1f} percentage points from last week",
)
col2.metric("Stored energy", f"{latest['fylling_TWh']:.2f} TWh")
col3.metric("Capacity", f"{latest['kapasitet_TWh']:.2f} TWh")

# ---------- Oversikt over sidene ----------
# Samme grupper som i menyen (Home.py), så det er lett å finne fram
st.subheader("What you can explore")
st.markdown(
    """
**Overview**
- **Map** – price and water areas coloured by fill level or weather for a chosen week. Click an area to select it
- **Reservoirs** – table and plot of reservoir data for the selected area type
- **Power exchange** – power flow in and out of Norway on each cross-border connection

**Analysis**
- **Reservoir analysis** – STL decomposition and spectrogram of the fill level
- **Weather outliers** – outliers (SPC) and anomalies (LOF) in weather data

**Prediction**
- **Correlation** – sliding window correlation between weather and reservoirs, with lag
- **Forecast** – forecast of the fill level with SNARIMAX (River), with weather and exchange rates as optional inputs
"""
)
st.caption("The area selected in the sidebar (or by clicking in the map) is used on all pages "
           "except Home and Power exchange.")

# ---------- Om dataene ----------
st.subheader("About the data")
st.write(
    "The reservoir data is fetched directly from NVE's API (Magasinstatistikk). "
    "Weather data (ERA5) comes from open-meteo, and exchange rates for EUR and USD from Norges Bank. "
    "The cross-border power flows come from ENTSO-E and are stored in a MongoDB database."
)
