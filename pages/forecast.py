# Side i Prediction-gruppen: prognose av fyllingsgraden med SNARIMAX fra River.
# Brukeren velger treningsperiode (siste uke følger kartet), horisont, eksogene variabler
# og modellparametere. Resultatet vises som en animasjon der prognosen vokser uke for uke.
import pandas as pd
import plotly.express as px
import streamlit as st
from functions import (COLORS, HIGHLIGHT, LABELS, area_selector, download_exchange_rates,
                       forecast_fill_level, load_reservoirs, weekly_weather)

st.title("Forecast of Reservoir Fill Level")

area = area_selector()
reservoirs = load_reservoirs()
st.write("The model learns from the fill level week by week in the training period, and then "
         "forecasts the coming weeks. The default settings gave the most accurate forecasts "
         "when different models were tested on earlier years.")

# Fyllingsgraden for valgt område i prosent, med søndagen uka slutter på som indeks
fill = (reservoirs[reservoirs["area"] == area]
        .set_index("dato_Id")["fyllingsgrad"].sort_index() * 100)

# ---------- Tid (følger kartet) ----------
# Samme uker som i kartet: fra 2015 og fram til en uke siden (værdataene kommer med noen dagers forsinkelse)
last_allowed = pd.Timestamp.today().normalize() - pd.Timedelta(days=7)
dates = fill.index[(fill.index >= "2015-01-01") & (fill.index <= last_allowed)].tolist()


# Uka som er valgt i kartet brukes som siste uke i treningsdataene, og endringer her vises også i kartet.
# Slideren har sin egen nøkkel, og save_week kopierer valget til map_date (som på kartsiden).
def save_week():
    st.session_state["map_date"] = st.session_state["forecast_week"]

if st.session_state.get("map_date") not in dates:
    st.session_state["map_date"] = dates[-1]
st.session_state["forecast_week"] = st.session_state["map_date"]

col1, col2, col3 = st.columns(3)
train_end = col1.select_slider("Last week of training data (synced with the map):", options=dates,
                               key="forecast_week", on_change=save_week,
                               format_func=lambda d: d.strftime("%d %b %Y"))

years = col2.slider("Years of training data", 2, 4, 4,
                    help="At most 4 years, because of the download limit at open-meteo")
horizon = col3.slider("Forecast horizon (weeks)", 4, 52, 26)

# ---------- Eksogene variabler og modellparametere ----------
exog_names = {**LABELS, "EUR": "EUR exchange rate (NOK)", "USD": "USD exchange rate (NOK)"}
exog = st.multiselect("Exogenous variables:", list(exog_names.keys()),
                      default=["precipitation", "snowfall", "temperature_2m"],
                      format_func=exog_names.get)

with st.expander("Model parameters (SNARIMAX)"):
    c1, c2, c3, c4 = st.columns(4)
    p = c1.number_input("p (AR order)", 0, 6, 2)
    d = c2.number_input("d (differencing)", 0, 2, 1)
    q = c3.number_input("q (MA order)", 0, 4, 0)
    learning_rate = c4.select_slider("Learning rate", options=[0.0001, 0.001, 0.01, 0.1], value=0.001)
    c1, c2, c3, _ = st.columns(4)
    sp = c1.number_input("sp (seasonal AR)", 0, 2, 1)
    sd = c2.number_input("sd (seasonal differencing)", 0, 1, 0)
    sq = c3.number_input("sq (seasonal MA)", 0, 2, 0)
    st.caption("The season is 52 weeks. d = 1 means the model forecasts the weekly change in fill level.")

# ---------- Data ----------
train_start = train_end - pd.DateOffset(years=years)
# Ukene som skal spås: de neste horizon søndagene etter treningsperioden
future_dates = pd.date_range(train_end + pd.Timedelta(days=7), periods=horizon, freq="W-SUN")

# Værdata for hele kalenderår (så samme nedlasting kan gjenbrukes fra cachen), men ikke lenger
# enn open-meteo har data. 3 punkter holder nedlastingen under minuttgrensen.
weather_end = min(pd.Timestamp(f"{future_dates[-1].year}-12-31"), last_allowed)
weather = weekly_weather(area, f"{train_start.year}-01-01", weather_end.strftime("%Y-%m-%d"), n_points=3)

# Delene som skal i tabellen: fyllingsgrad og vær per uke
parts = [fill.rename("fill_level"), weather]
# Valutakursene lastes bare ned og tas med hvis de er valgt, som gjennomsnitt per uke
if "EUR" in exog or "USD" in exog:
    rates = download_exchange_rates(f"{train_start.year}-01-01",
                                    last_allowed.strftime("%Y-%m-%d")).resample("W-SUN").mean()
    parts.append(rates)

# Én tabell med alle delene, koblet på datoen (søndagen uka slutter på)
table = pd.concat(parts, axis=1)
train = table.loc[train_start:train_end].dropna(subset=["fill_level"] + exog)
future = table.reindex(future_dates)

# Uker uten værdata (framtiden) får normalt vær: gjennomsnittet for samme uke i treningsårene.
# Valutakurser uten verdi får siste kjente kurs.
missing_weeks = int(future[exog].isna().any(axis=1).sum()) if exog else 0
train_weeks = train.index.isocalendar().week
future_weeks = future.index.isocalendar().week.values
for column in exog:
    if column in LABELS:
        normal = train[column].groupby(train_weeks).mean().reindex(future_weeks).values
        future[column] = future[column].fillna(pd.Series(normal, index=future.index))
    else:
        future[column] = future[column].fillna(train[column].iloc[-1])
    # Sikkerhetsnett, f.eks. for uke 53 som ikke finnes i alle år
    future[column] = future[column].fillna(train[column].mean())

if missing_weeks > 0:
    st.info(f"Weather data is not available for {missing_weeks} of the forecast weeks. "
            "For these weeks, the normal weather (average for the same week in the training years) is used.")

# ---------- Prognose ----------
with st.spinner("Training the model and forecasting ..."):
    forecast = forecast_fill_level(train, future, exog=exog, p=int(p), d=int(d), q=int(q),
                                   sp=int(sp), sd=int(sd), sq=int(sq), learning_rate=learning_rate)

# Nøkkeltall. MAE vises bare hvis de faktiske verdiene er kjent (når prognosen gjelder fortiden).
actual = future["fill_level"].dropna()
col1, col2, col3 = st.columns(3)
col1.metric("Last observed fill level", f"{train['fill_level'].iloc[-1]:.1f} %")
col2.metric(f"Forecast in {horizon} weeks", f"{forecast.iloc[-1]:.1f} %")
if len(actual) > 0:
    mae = (actual - forecast.loc[actual.index]).abs().mean()
    col3.metric("Mean absolute error (percentage points)", f"{mae:.1f}")

# ---------- Animert plott ----------
# Observert: de to siste årene av treningsperioden og de faktiske verdiene etterpå (hvis kjent)
observed = pd.concat([train["fill_level"].iloc[-104:], actual])
# Prognosen starter i siste observerte uke, så linjene henger sammen
forecast_line = pd.concat([train["fill_level"].iloc[-1:], forecast])

# Ett bilde (frame) per uke: den observerte linja er med i alle, mens prognosen vokser én uke om gangen
frames = []
for step in range(2, len(forecast_line) + 1):
    frame = pd.concat([
        pd.DataFrame({"Week": observed.index, "Fill level (%)": observed.values, "Series": "Observed"}),
        pd.DataFrame({"Week": forecast_line.index[:step], "Fill level (%)": forecast_line.values[:step],
                      "Series": "Forecast"}),
    ])
    frame["Weeks ahead"] = step - 1
    frames.append(frame)
animation = pd.concat(frames)

fig = px.line(animation, x="Week", y="Fill level (%)", color="Series", animation_frame="Weeks ahead",
              color_discrete_map={"Observed": COLORS[0], "Forecast": HIGHLIGHT},
              range_x=[observed.index[0], future_dates[-1]], range_y=[0, 100],
              title=f"Forecast of fill level for {area} ({horizon} weeks ahead)")
# Grått felt med tekst for perioden som spås
fig.add_vrect(x0=train.index[-1], x1=future_dates[-1], fillcolor="grey", opacity=0.1, line_width=0,
              annotation_text="Forecast period", annotation_position="top left")
# Litt raskere animasjon (100 ms per uke)
fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = 100
# legend_title_text="" fjerner overskriften "Series" over forklaringen
fig.update_layout(height=550, legend_title_text="",
                  legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
st.plotly_chart(fig, width="stretch")

st.caption("Press ▶ to see the forecast grow week by week. The forecast is dynamic: each week is "
           "forecast from the model's own forecasts for the weeks before. The grey area is the forecast period.")

with st.expander("Show forecast table"):
    # Tabell med prognosen, og de faktiske verdiene hvis de er kjent
    forecast_table = pd.DataFrame({"Forecast (%)": forecast})
    if len(actual) > 0:
        forecast_table["Observed (%)"] = future["fill_level"]
    forecast_table.index = forecast_table.index.strftime("%d %b %Y")   # bare datoen, uten klokkeslett
    forecast_table.index.name = "Week ending"
    st.dataframe(forecast_table.round(1), width="stretch")