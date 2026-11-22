# Side i Prediction-gruppen: sliding window-korrelasjon mellom vær og magasinstatistikk.
# Brukeren velger værvariabel, magasinvariabel, år, lag og vindulengde.
# Området velges i sidebaren (eller ved å klikke i kartet).
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from functions import COLORS, HIGHLIGHT, LABELS, area_selector, load_reservoirs, weekly_weather

st.title("Weather and Reservoirs: Sliding Window Correlation")

area = area_selector()
reservoirs = load_reservoirs()

st.write("The correlation between a weather property and the reservoirs is calculated in a window "
         "that slides through time. The lag moves the weather forward in time, so you can see if the "
         "weather affects the reservoirs some weeks later.")

# ---------- Valg ----------
# Magasinvariablene som kan velges, med lesbare navn
reservoir_options = {
    "fyllingsgrad": "Fill level (%)",
    "endring_fyllingsgrad": "Weekly change in fill level (percentage points)",
}
col1, col2 = st.columns(2)
variable = col1.selectbox("Weather property:", list(LABELS.keys()), format_func=LABELS.get)
reservoir_col = col2.selectbox("Reservoir variable:", list(reservoir_options.keys()),
                               format_func=reservoir_options.get)

col1, col2, col3 = st.columns(3)
start_year, end_year = col1.select_slider("Years:", options=list(range(2015, 2026)),
                                          value=(2021, 2024))
lag = col2.slider("Lag (weeks)", 0, 26, 0,
                  help="The weather is compared with the reservoirs this many weeks later")
window = col3.slider("Window length (weeks)", 8, 104, 26, step=2)

# Open-meteo har en grense for hvor mye som kan lastes ned per minutt,
# så det vises høyst 4 år om gangen
if end_year - start_year > 3:
    start_year = end_year - 3
    st.info(f"At most 4 years can be shown at a time. Showing {start_year}–{end_year}.")

# ---------- Data ----------
# Ukentlige værdata for området og fyllingsgraden for samme område
weather = weekly_weather(area, f"{start_year}-01-01", f"{end_year}-12-31")[variable]
reservoir = (reservoirs[reservoirs["area"] == area]
             .set_index("dato_Id")[reservoir_col] * 100)   # * 100 gir prosent

# Kobler de to seriene på datoen (søndagen uka slutter på). join="inner" beholder bare uker som finnes i begge.
data = pd.concat([weather.rename("weather"), reservoir.rename("reservoir")],
                 axis=1, join="inner").sort_index()

# Lag: været flyttes lag uker fram, så uke t i magasinene sammenlignes med været i uke t - lag
data["weather_lagged"] = data["weather"].shift(lag)

# Sliding window-korrelasjon: korrelasjonen i et vindu på window uker, sentrert rundt hver uke
data["correlation"] = data["weather_lagged"].rolling(window, center=True).corr(data["reservoir"])

# Korrelasjonen for hele perioden med valgt lag, som et nøkkeltall
overall = data["weather_lagged"].corr(data["reservoir"])
st.metric(f"Correlation for the whole period (lag {lag} weeks)", f"{overall:.2f}")

# ---------- Plott ----------
# Tre plott under hverandre med felles x-akse: værvariabelen, magasinvariabelen og korrelasjonen
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06)
fig.add_trace(go.Scatter(x=data.index, y=data["weather"], mode="lines",
                         name=LABELS[variable], line=dict(color=COLORS[0])), row=1, col=1)
fig.add_trace(go.Scatter(x=data.index, y=data["reservoir"], mode="lines",
                         name=reservoir_options[reservoir_col], line=dict(color=COLORS[2])), row=2, col=1)
fig.add_trace(go.Scatter(x=data.index, y=data["correlation"], mode="lines",
                         name="Correlation", line=dict(color=HIGHLIGHT)), row=3, col=1)

# Nullinje i korrelasjonsplottet, og fast skala fra -1 til 1
fig.add_hline(y=0, line_color="grey", line_width=1, row=3, col=1)
fig.update_yaxes(title_text=LABELS[variable], row=1, col=1)
fig.update_yaxes(title_text=reservoir_options[reservoir_col], row=2, col=1)
fig.update_yaxes(title_text="Correlation", range=[-1, 1], row=3, col=1)
fig.update_xaxes(title_text="Week (ending on Sunday)", row=3, col=1)
fig.update_layout(
    title=f"{LABELS[variable]} vs {reservoir_options[reservoir_col]} in {area} "
          f"(lag = {lag} weeks, window = {window} weeks)",
    height=750,
    showlegend=False,   # navnene står på y-aksene
)
st.plotly_chart(fig, width="stretch")

st.caption("Weather is aggregated per week (Monday to Sunday, Norwegian time): weekly totals for "
           "precipitation, rain and snowfall, weekly means for the others. "
           "Correlation near 1: the two move together. Near −1: they move in opposite directions. "
           "Near 0: no clear relationship.")