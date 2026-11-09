# Felles funksjoner for sidene i appen.
# Analysefunksjonene er de samme som i notebooks/analyse_part3.ipynb,
# men værdata og magasindata caches med st.cache_data, så de bare lastes ned én gang.

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import requests
import streamlit as st
import openmeteo_requests
from retry_requests import retry
from scipy.fft import dct, idct
from scipy import stats
from scipy.signal import stft
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.seasonal import STL

# Områdenumrene som har magasindata for hver områdetype.
AREAS = {"EL": [1, 2, 3, 4, 5], "NO": [0], "VASS": [1, 2, 3]}

# Værvariablene som lastes ned, og lesbare navn med enheter til plottene.
VARIABLES = ["temperature_2m", "precipitation", "rain", "snowfall",
             "wind_speed_10m", "relative_humidity_2m"]
LABELS = {"temperature_2m": "Temperature (°C)", "precipitation": "Precipitation (mm)",
          "rain": "Rain (mm)", "snowfall": "Snowfall (cm)",
          "wind_speed_10m": "Wind speed (km/h)", "relative_humidity_2m": "Relative humidity (%)"}


# ---------- Felles områdevalg ----------
#area_selector lager områdevalget i sidebaren
def area_selector():
    """Viser områdevalget i sidebaren og returnerer valgt område, f.eks. "EL 3".

    Valget lagres i st.session_state, så det huskes når brukeren bytter side.
    """
    # Standardvalg første gang appen åpnes: NO3 (EL 3), som i notebooken.
    if "area_type" not in st.session_state:
        st.session_state["area_type"] = "EL"
        st.session_state["area_number"] = 3

    st.sidebar.subheader("Area (used on all pages)")
    types = list(AREAS.keys())
    area_type = st.sidebar.radio("Area type:", types, horizontal=True,
                                 index=types.index(st.session_state["area_type"]))

    # Hvis forrige nummer ikke finnes for den nye typen (f.eks. VASS 5), velges det første.
    numbers = AREAS[area_type]
    current = st.session_state["area_number"]
    if current not in numbers:
        current = numbers[0]
    area_number = st.sidebar.selectbox("Area number:", numbers, index=numbers.index(current))

    #Valget lagres i st.session_state. Det er minnet til appen, og det gjør at valget huskes når man bytter side.
    st.session_state["area_type"] = area_type
    st.session_state["area_number"] = area_number
    st.sidebar.caption("EL = price areas, NO = whole country, VASS = watercourse areas")
    return f"{area_type} {area_number}"


# ---------- Henting av data ----------

@st.cache_data(ttl=86400)
def load_reservoirs():
    """Henter magasinstatistikken fra NVE sitt API (samme som i notebooken)."""
    url = "https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk/HentOffentligData"
    reservoirs = pd.DataFrame(requests.get(url).json())
    reservoirs["dato_Id"] = pd.to_datetime(reservoirs["dato_Id"])
    reservoirs["area"] = reservoirs["omrType"] + " " + reservoirs["omrnr"].astype(str)
    return reservoirs
# Funksjonen download_weather leser denne fila og plukker ut punktene for området som er valgt i sidebaren.
@st.cache_data(show_spinner="Downloading weather data from open-meteo ...") #Med caching lastes hvert område og år bare ned én gang
def download_weather(area, year, n_points=20): #Appen bruker 20 punkter, open-meteo har en grense for hvor mye som kan lastes ned
    """Laster ned værdata (ERA5, timesverdier) for et område og ett år.

    Bruker de tilfeldige punktene i data/locations.csv (laget i notebooken).
    20 punkter holder nedlastingen under minuttgrensen hos open-meteo.
    Returnerer gjennomsnittet over punktene for hver time (tid i UTC).
    """
    # I notebooken trakk jeg 1000 tilfeldige punkter i hvert område og lagret dem i fila locations.csv.
    locations = pd.read_csv("data/locations.csv")
    if area == "NO 0":
        # Hele landet: et tilfeldig utvalg av punktene fra alle strømprisområdene.
        el_points = locations[locations["area"].str.startswith("EL")]
        points = el_points.sample(n_points, random_state=42)
    else:
        points = locations[locations["area"] == area].head(n_points)

    # Open-meteo-klienten prøver på nytt hvis en forespørsel feiler.
    openmeteo = openmeteo_requests.Client(
        session=retry(requests.Session(), retries=5, backoff_factor=0.2))
    params = {
        "latitude": points["latitude"].tolist(),
        "longitude": points["longitude"].tolist(),
        "start_date": f"{year}-01-01",
        "end_date": f"{year}-12-31",
        "hourly": VARIABLES,
        "models": "era5",
    }
    responses = openmeteo.weather_api("https://archive-api.open-meteo.com/v1/archive",
                                      params=params)

    # Ett svar per punkt. Gjør hvert svar om til en tabell med tid og alle variablene.
    all_points = []
    for response in responses:
        hourly = response.Hourly()
        df = pd.DataFrame({"time": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left",
        )})
        for i, variable in enumerate(VARIABLES):
            df[variable] = hourly.Variables(i).ValuesAsNumpy()
        all_points.append(df)

    # Gjennomsnittet av alle punktene for hver time.
    return pd.concat(all_points).groupby("time").mean()


# ---------- Uteliggere med SPC ----------
# Definerer funksjonen spc_outliers, som er den samme som i notebooken. Den finner uteliggerne i fem steg: 

def spc_outliers(weather, column="precipitation", cutoff=100, n_std=3):
    """Finner uteliggere med SPC basert på SATV (høypassfiltrert serie med DCT).

    weather: tabell med tid som indeks (fra download_weather)
    column:  variabelen som analyseres, standard er nedbør
    cutoff:  DCT-indeks. Frekvenser under denne settes til null (high-pass).
    n_std:   antall robuste standardavvik til grensene

    Returnerer figuren, en oppsummering og en tabell med uteliggerne.
    """
    values = weather[column].values

    # 1. DCT: fra tidsserie til frekvenser (samme type og norm som i D2Dbook)
    coeffs = dct(values, type=1, norm="forward")

    # 2. High-pass: fjerner de langsomme svingningene og gjør om tilbake. Resultatet er SATV.
    coeffs_high = coeffs.copy()
    coeffs_high[:cutoff] = 0
    satv = idct(coeffs_high, type=1, norm="forward")

    # 3. Den langsomme kurven (det som ble fjernet)
    trend = values - satv

    # 4. Robust statistikk på SATV for hele året: median og MAD skalert til standardavvik (× 1,4826)
    center = np.median(satv)
    sigma = stats.median_abs_deviation(satv, scale="normal")

    # 5. Grenser rundt den langsomme kurven, og uteliggere der SATV er utenfor grensene
    upper = trend + center + n_std * sigma
    lower = trend + center - n_std * sigma
    is_outlier = (satv > center + n_std * sigma) | (satv < center - n_std * sigma)

    # Plott: serien, grensene og uteliggerne i en kontrastfarge (SATV plottes ikke)
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(weather.index, values, color="tab:blue", linewidth=0.6, label=LABELS[column])
    ax.plot(weather.index, upper, color="grey", linestyle="--", linewidth=0.8, label="SPC limits")
    ax.plot(weather.index, lower, color="grey", linestyle="--", linewidth=0.8)
    ax.scatter(weather.index[is_outlier], values[is_outlier], color="tab:red", s=10,
               zorder=3, label="Outliers")
    ax.set_title(f"{LABELS[column]} with SPC limits "
                 f"(cutoff = {cutoff}, {n_std} robust SDs)")
    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel(LABELS[column])
    ax.legend(loc="upper right")
    ax.grid(alpha=0.3)
    plt.tight_layout()

    # Oversikt over uteliggerne
    outliers = weather.loc[is_outlier, [column]]
    summary = {
        "number of outliers": int(is_outlier.sum()),
        "share of outliers (%)": round(float(100 * is_outlier.mean()), 2),
        "robust SD (SATV)": round(float(sigma), 3),
    }
    return fig, summary, outliers


# ---------- Anomalier med LOF ----------

def lof_anomalies(weather, column="temperature_2m", contamination=0.01, n_neighbors=20):
    """Finner anomalier med Local Outlier Factor (LOF).

    weather:       tabell med tid som indeks (fra download_weather)
    column:        variabelen som analyseres, standard er temperatur
    contamination: andelen anomalier, standard 1 %
    n_neighbors:   antall naboer LOF sammenligner med

    Returnerer figuren, en oppsummering og en tabell med anomaliene.
    """
    values = weather[column].values

    # Tid som antall timer fra start, så LOF ser hvilke timer som ligger nær hverandre
    hours = (weather.index - weather.index[0]) / pd.Timedelta(hours=1)

    # Skalerer tid og verdi til gjennomsnitt 0 og standardavvik 1, så de teller like mye
    X = StandardScaler().fit_transform(np.column_stack([hours, values]))

    # LOF gir -1 for anomalier og 1 for vanlige punkter
    lof = LocalOutlierFactor(n_neighbors=n_neighbors, contamination=contamination)
    is_anomaly = lof.fit_predict(X) == -1

    # Plott: serien og anomaliene i en kontrastfarge
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(weather.index, values, color="tab:blue", linewidth=0.6, label=LABELS[column])
    ax.scatter(weather.index[is_anomaly], values[is_anomaly], color="tab:red", s=10,
               zorder=3, label="Anomalies (LOF)")
    ax.set_title(f"{LABELS[column]} with LOF anomalies "
                 f"(proportion = {contamination * 100:g} %, {n_neighbors} neighbours)")
    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel(LABELS[column])
    ax.legend(loc="upper right")
    ax.grid(alpha=0.3)
    plt.tight_layout()

    # Oversikt over anomaliene
    anomalies = weather.loc[is_anomaly, [column]]
    summary = {
        "number of anomalies": int(is_anomaly.sum()),
        "share of anomalies (%)": round(float(100 * is_anomaly.mean()), 2),
        "lowest anomaly": round(float(anomalies[column].min()), 2),
        "highest anomaly": round(float(anomalies[column].max()), 2),
    }
    return fig, summary, anomalies


# ---------- STL-dekomponering ----------

def stl_plot(reservoirs, area="EL 3", period=52, seasonal=13, trend=105, robust=False):
    """STL-dekomponering av fyllingsgraden for ett område.

    reservoirs: magasinstatistikken fra NVE
    area:       område, f.eks. "EL 3" eller "VASS 1"
    period:     antall uker i én sesong (ett år)
    seasonal:   glatting av sesongen (oddetall)
    trend:      glatting av trenden i uker (oddetall, større enn period)
    robust:     True gjør metoden mindre følsom for store avvik

    Returnerer figuren.
    """
    # Fyllingsgraden for området som en tidsserie med dato som indeks, sortert etter dato
    series = (reservoirs[reservoirs["area"] == area]
              .sort_values("dato_Id")
              .set_index("dato_Id")["fyllingsgrad"] * 100)   # * 100 gir prosent

    # STL med valgte parametere
    result = STL(series, period=period, seasonal=seasonal, trend=trend, robust=robust).fit()

    # Plotter de fire delene under hverandre: data, trend, sesong og rest
    fig = result.plot()
    fig.set_size_inches(10, 7)
    fig.suptitle(f"STL of fill level (%) for {area} "
                 f"(seasonal = {seasonal}, trend = {trend}, robust = {robust})", y=1.01)
    for ax in fig.axes:
        ax.grid(alpha=0.3)

    # Lesbare navn på aksene
    fig.axes[0].set_title("")                     # fjerner den doble overskriften
    fig.axes[0].set_ylabel("Fill level (%)")
    fig.axes[1].set_ylabel("Trend")
    fig.axes[2].set_ylabel("Season")
    fig.axes[3].set_ylabel("Residual")
    fig.axes[-1].set_xlabel("Date")

    # Mindre prikker i restplottet, så det blir lettere å lese
    fig.axes[3].lines[0].set_markersize(2)
    plt.tight_layout()
    return fig


# ---------- Spektrogram ----------

def spectrogram_plot(reservoirs, area="EL 3", window_length=104, overlap=78):
    """Spektrogram av fyllingsgraden for ett område.

    reservoirs:    magasinstatistikken fra NVE
    area:          område, f.eks. "EL 3" eller "VASS 1"
    window_length: lengden på hvert vindu i uker
    overlap:       antall uker vinduene overlapper (må være mindre enn window_length)

    Returnerer figuren.
    """
    series = (reservoirs[reservoirs["area"] == area]
              .sort_values("dato_Id")
              .set_index("dato_Id")["fyllingsgrad"] * 100)

    # STFT: fs=52 målinger per år, så frekvensen blir svingninger per år.
    # detrend="constant" trekker fra gjennomsnittet i hvert vindu.
    f, t, Zxx = stft(series.values, fs=52, nperseg=window_length,
                     noverlap=overlap, detrend="constant")

    # t er år fra starten av serien. Legger til startåret, så x-aksen viser årstall.
    years = series.index[0].year + t

    fig, ax = plt.subplots(figsize=(10, 4))
    mesh = ax.pcolormesh(years, f, np.abs(Zxx), shading="gouraud", cmap="viridis")
    fig.colorbar(mesh, ax=ax, label="Magnitude")
    ax.set_ylim(0, 6)   # viser de laveste frekvensene, der det meste skjer
    ax.set_title(f"Spectrogram of fill level for {area} "
                 f"(window = {window_length} weeks, overlap = {overlap} weeks)")
    ax.set_xlabel("Year")
    ax.set_ylabel("Frequency (cycles per year)")
    plt.tight_layout()
    return fig