# IND320 Dashboard – Norwegian Hydropower Reservoirs

A Streamlit dashboard made in the course **IND320 Data to Decision** at NMBU (autumn 2026).
The app explores Norwegian hydropower reservoir levels, weather data and cross-border power exchange,
and forecasts the reservoir fill level with SNARIMAX (River), using weather and exchange rates as optional inputs.

- **Streamlit app:** https://ind320-dashboard-kaja321.streamlit.app/
- **Author:** Kaja Andreassen Tessem

## Data sources

| Source | What | How it is used |
|---|---|---|
| [NVE Magasinstatistikk](https://biapi.nve.no/magasinstatistikk/) | Weekly reservoir fill level per area (EL, NO, VASS) | Fetched directly from the API in the app |
| [open-meteo](https://open-meteo.com/) (ERA5) | Hourly historical weather | Downloaded in the app for the selected area and period, and aggregated to weeks when needed |
| [ENTSO-E](https://transparency.entsoe.eu/) | Physical cross-border power flows | Fetched in the notebook, stored via Cassandra/Spark, saved in MongoDB |
| [NVE Atlas](https://atlas.nve.no/) | Shapefiles for price areas and NVE regions | Converted to GeoJSON for the map, and used to sample random locations |
| [Norges Bank](https://data.norges-bank.no/) | Daily EUR and USD exchange rates (NOK) | Downloaded in the app as optional input to the forecast |

Hourly data (open-meteo, ENTSO-E) is kept in UTC. When weather is combined with the reservoir data, it is converted to Norwegian time and aggregated to weeks ending on Sunday, like Magasinstatistikk.

## Pages in the app

The menu is grouped in the same way as the sketch in `notebooks/analyse_part4.ipynb`:

- **Home** – introduction and latest fill level
- **Overview**
  - **Map** – areas coloured by fill level or weather for a chosen week; a click selects the area
  - **Reservoirs** – table and plot of reservoir data for the selected area type
  - **Power exchange** – net power flow in and out of Norway on each connection
- **Analysis**
  - **Reservoir analysis** – STL decomposition and spectrogram of the fill level
  - **Weather outliers** – outliers (SPC) and anomalies (LOF) in weather data
- **Prediction**
  - **Correlation** – sliding window correlation between weather and reservoirs
  - **Forecast** – SNARIMAX forecast of the fill level with Plotly animation

The selected area and the selected week are stored in `st.session_state`, so they are remembered when moving between pages. The week is shared by the map and the forecast.

## Repository structure

```
Home.py               starts the app and builds the grouped menu (st.navigation)
pages/                the pages of the app (home.py is the front page)
functions.py          shared functions and colours used by the pages
requirements.txt      Python packages needed by the app
.streamlit/           config.toml (theme); secrets.toml is not in the repository
data/                 shapefiles from NVE Atlas, GeoJSON files for the map and locations.csv
notebooks/            Jupyter notebooks for part 1–4 and the app sketch (sketch.png)
recordings/           screencast for part 1 (later videos are linked in the notebooks)
```

**Why `data/locations.csv`?** The notebook samples 1000 random locations in each area with geopandas.
They are saved as a small CSV file so the app can use the same locations without needing geopandas,
which is hard to install. The file does not change, so it is a deliberate exception to storing data in the database.

## Run the app locally

1. Clone the repository and create a virtual environment (Python 3.11):
   ```bash
   git clone https://github.com/Kaja321/ind320-dashboard-kaja321.git
   cd ind320-dashboard-kaja321
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Add the MongoDB connection in `.streamlit/secrets.toml` (this file is not in the repository):
   ```toml
   [mongo]
   uri = "mongodb+srv://<user>:<password>@<cluster>.mongodb.net/"
   ```
3. Start the app:
   ```bash
   streamlit run Home.py
   ```

The notebooks are run from the `notebooks/` folder, so file paths in them start with `../`.