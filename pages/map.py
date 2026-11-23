# Side i Overview-gruppen: interaktivt kart over områdene i magasinstatistikken.
# Områdene tegnes fra GeoJSON-filene (laget i notebooken for del 4) og fargelegges etter
# fyllingsgrad eller en værvariabel for uka som velges med slideren.
# Et klikk i et område lagrer det som valgt område, så de andre sidene bruker det.
import json
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from functions import HIGHLIGHT, LABELS, area_selector, download_weather, load_reservoirs

st.title("Map of Areas")


# Leser en GeoJSON-fil. st.cache_data gjør at fila bare leses én gang.
@st.cache_data
def load_geojson(path):
    with open(path) as f:
        return json.load(f)


# ---------- Klikk i kartet ----------
# Kartet har key="map", så Streamlit lagrer det siste klikket i st.session_state["map"].
# Klikket leses her, før områdevalget i sidebaren lages, så sidebaren viser området man klikket på.
# last_click sørger for at et gammelt klikk ikke overstyrer et senere valg i sidebaren.
event = st.session_state.get("map")
if event and event["selection"]["points"]:
    point = event["selection"]["points"][0]
    # curve_number 0 er områdene. (Omrisset av valgt område er et eget lag, som ikke skal telle.)
    if point.get("curve_number", 0) == 0:
        # Områdenavnet, f.eks. "EL 2". Hvis det mangler, slås det opp med punktets nummer
        # i lista over områdene i kartet som ble klikket på.
        clicked = point.get("location") or st.session_state["map_areas"][point["point_index"]]
        if clicked != st.session_state.get("last_click"):
            area_type, area_number = clicked.split()
            st.session_state["area_type"] = area_type
            st.session_state["area_number"] = int(area_number)
            st.session_state["last_click"] = clicked

area = area_selector()
reservoirs = load_reservoirs()

# ---------- Valg ----------
col1, col2 = st.columns([1, 2])
# Hva områdene skal fargelegges etter
# Starter på vassdragsområder hvis et VASS-område er valgt i sidebaren, ellers prisområder.
# Når valget i sidebaren endres, følger kartet etter.
start_index = 1 if area.startswith("VASS") else 0
color_by = col1.radio("Colour by:", ["Price areas (fill level)", "Water areas (fill level)",
                                     "Weather property"], index=start_index)
if color_by == "Weather property":
    variable = col1.selectbox("Weather property:", list(LABELS.keys()), format_func=LABELS.get)

# Ukene som kan velges: datoene i magasinstatistikken (søndager, siste dag i uka) fra 2015.
# De siste 7 dagene tas ikke med, fordi værdataene fra open-meteo kommer med noen dagers forsinkelse.
all_dates = pd.Series(reservoirs["dato_Id"].unique()).sort_values()
last_allowed = pd.Timestamp.today() - pd.Timedelta(days=7)
dates = all_dates[(all_dates >= "2015-01-01") & (all_dates <= last_allowed)].tolist()

# Valgt uke huskes i session_state, så den kan brukes på andre sider (f.eks. prognosen)
default = st.session_state.get("map_date", dates[-1])
if default not in dates:
    default = dates[-1]
date = col2.select_slider("Select week (ending on):", options=dates, value=default,
                          format_func=lambda d: d.strftime("%d %b %Y"))
st.session_state["map_date"] = date

# ---------- Data til kartet ----------
# Vassdragsområdene (VASS) eller prisområdene (EL). Værdata vises for prisområdene.
if color_by == "Water areas (fill level)":
    geojson = load_geojson("data/water_areas.geojson")
else:
    geojson = load_geojson("data/price_areas.geojson")
# Områdenavnene i GeoJSON-fila, f.eks. ["EL 1", "EL 2", ...]
areas = [feature["properties"]["area"] for feature in geojson["features"]]

if color_by == "Weather property":
    # Værdata for uka (mandag til søndag) i hvert område. 10 punkter per område holder for et
    # gjennomsnitt og gjør nedlastingen rask. Tidene er i UTC, så uka er forskjøvet 1–2 timer.
    start = (date - pd.Timedelta(days=6)).strftime("%Y-%m-%d")
    end = date.strftime("%Y-%m-%d")
    values = []
    for name in areas:
        weather = download_weather(name, start, end, n_points=10)
        # Nedbør, regn og snø summeres over uka. De andre variablene er gjennomsnitt.
        if variable in ["precipitation", "rain", "snowfall"]:
            values.append(weather[variable].sum())
        else:
            values.append(weather[variable].mean())
    color_label = LABELS[variable]
    colorscale = "Viridis"
else:
    # Fyllingsgraden for uka i hvert område, i samme rekkefølge som i GeoJSON-fila
    week = reservoirs[reservoirs["dato_Id"] == date].set_index("area").reindex(areas)
    values = (week["fyllingsgrad"] * 100).tolist()
    color_label = "Fill level (%)"
    colorscale = "Blues"

# Lagrer lista over områdene, så et klikk kan slås opp ved neste kjøring (se øverst)
st.session_state["map_areas"] = areas

# ---------- Kart ----------
fig = go.Figure()
# Områdene, fargelagt etter verdien. marker_opacity gjør fargene gjennomsiktige,
# og marker_line gir hvite omriss mellom områdene.
fig.add_trace(go.Choroplethmap(
    geojson=geojson,
    featureidkey="properties.area",   # kobler hvert område i GeoJSON-fila med navnet i locations
    locations=areas,
    z=values,
    colorscale=colorscale,
    marker_opacity=0.6,
    marker_line_width=1,
    marker_line_color="white",
    colorbar=dict(title=dict(text=color_label, side="right")),   # tittelen langs siden, så den er lett å lese
    hovertemplate="%{location}: %{z:.1f}<extra></extra>",
    # Samme gjennomsiktighet før og etter klikk (Plotly gjør ellers de andre områdene blekere)
    selected=dict(marker=dict(opacity=0.6)),
    unselected=dict(marker=dict(opacity=0.6)),
))
# Valgt område får et tykt omriss i kontrastfargen (fyllet er helt gjennomsiktig).
# Er hele landet (NO 0) valgt, får alle områdene omriss.
highlight = areas if area == "NO 0" else [area]
if area in areas or area == "NO 0":
    fig.add_trace(go.Choroplethmap(
        geojson=geojson,
        featureidkey="properties.area",
        locations=highlight,
        z=[0] * len(highlight),
        colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
        showscale=False,
        marker_line_width=4,
        marker_line_color=HIGHLIGHT,
        hoverinfo="skip",
    ))
fig.update_layout(
    map=dict(style="carto-positron", center={"lat": 65, "lon": 15}, zoom=3.4),
    height=650,
    margin=dict(l=0, r=0, t=0, b=0),
)
# on_select="rerun" kjører siden på nytt når man klikker, og klikket lagres i st.session_state["map"]
st.plotly_chart(fig, key="map", on_select="rerun", selection_mode="points", width="stretch")

# Forklaring under kartet: hvordan man velger område, og hva fargene viser
st.caption(f"Selected area: {area}. Click on an area to select it, or choose NO in the sidebar "
           "for the whole country.")
st.caption("Each area has one colour, showing the average for the whole area in the selected week: "
           "the fill level, or the weather property (weekly total for precipitation, rain and snowfall, "
           "weekly mean for the others).")