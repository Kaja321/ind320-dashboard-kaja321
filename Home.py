# Startfila til appen. Den setter opp menyen og kjører siden brukeren har valgt.
# Selve forsiden ligger i pages/home.py.
import streamlit as st

# Innstillinger for hele appen: tittel i nettleserfanen og bred layout
st.set_page_config(page_title="IND320 Dashboard", layout="wide")

# Sidene gruppert slik som i skissen. Nøkkelen er overskriften i menyen.
# Tom overskrift ("") gjør at Home står øverst uten overskrift.
# icon viser et lite symbol foran sidenavnet (Material Icons, innebygd i Streamlit),
# så menyen blir lettere å lese og sidene lettere å skille fra hverandre.
pages = {
    "": [
        # default=True gjør at Home vises når appen åpnes
        st.Page("pages/home.py", title="Home", icon=":material/home:", default=True),
    ],
    "Overview": [
        st.Page("pages/1_Reservoirs.py", title="Reservoirs", icon=":material/water_drop:"),
        st.Page("pages/4_Power_exchange.py", title="Power exchange", icon=":material/bolt:"),
    ],
    "Analysis": [
        st.Page("pages/2_Reservoir_analysis.py", title="Reservoir analysis", icon=":material/insights:"),
        st.Page("pages/3_Weather_outliers.py", title="Weather outliers", icon=":material/thermostat:"),
    ],
}

# Lager menyen i sidebaren og kjører siden som er valgt
page = st.navigation(pages)
page.run()