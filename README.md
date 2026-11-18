# IND320 Dashboard – Norwegian Hydropower Reservoirs

A Streamlit dashboard made in the course **IND320 Data to Decision** at NMBU (autumn 2026).
The app explores Norwegian hydropower reservoir levels, weather data and cross-border power exchange.

- **Streamlit app:** https://ind320-dashboard-kaja321.streamlit.app/
- **Author:** Kaja Andreassen Tessem

<!-- TODO del 4: legg til en setning om prognose av fyllingsgrad og valutakurser når det er ferdig -->

## Data sources

| Source | What | How it is used |
|---|---|---|
| [NVE Magasinstatistikk](https://biapi.nve.no/magasinstatistikk/) | Weekly reservoir fill level per area (EL, NO, VASS) | Fetched directly from the API in the app |
| [open-meteo](https://open-meteo.com/) (ERA5) | Hourly historical weather | Downloaded in the app for the selected area and year |
| [ENTSO-E](https://transparency.entsoe.eu/) | Physical cross-border power flows | Fetched in the notebook, stored via Cassandra/Spark, saved in MongoDB |
| [NVE Atlas](https://atlas.nve.no/) | Shapefiles for price areas and NVE regions | Used to draw the areas and sample random locations |
<!-- TODO del 4: legg til Norges Bank (valutakurser for EUR og USD) -->

All times are in UTC.

## Pages in the app

<!-- TODO del 4: oppdater listen når den nye sidestrukturen er bestemt -->
- **Home** – introduction and latest fill level
- **Reservoirs** – table and plot of reservoir data for the selected area type
- **Reservoir analysis** – STL decomposition and spectrogram of the fill level
- **Weather outliers** – outliers (SPC) and anomalies (LOF) in weather data
- **Power exchange** – power flow in and out of Norway on each connection

The area selected in the sidebar is stored in `st.session_state`, so it is remembered when moving between the pages that use it.

## Repository structure

<!-- TODO del 4: oppdater mappene hvis noe er flyttet eller lagt til -->
```
Home.py               front page of the Streamlit app
pages/                the other pages of the app
functions.py          shared functions used by the pages
requirements.txt      Python packages needed by the app
data/                 shapefiles from NVE Atlas and locations.csv
notebooks/            Jupyter notebooks for part 1–4 (development and documentation)
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