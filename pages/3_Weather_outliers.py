# Side 3: Uteliggere og anomalier i værdata for valgt område.
# Værdataene lastes ned fra open-meteo i bakgrunnen for området som er valgt i sidebaren,
# og caches, så samme område og år bare lastes ned én gang.
# Fane 1: SPC (uteliggere). Fane 2: LOF (anomalier).
import matplotlib.pyplot as plt
import streamlit as st
from functions import LABELS, area_selector, download_weather, spc_outliers, lof_anomalies

st.set_page_config(layout="wide")
st.title("Weather Outliers and Anomalies")

area = area_selector()
# År er et lokalt valg som bare gjelder denne siden. 2024 er standard, som i notebooken.
# st.columns(4)[0] gjør valget smalere, så det ikke fyller hele bredden.
year = st.columns(4)[0].selectbox("Select year:", list(range(2020, 2026)), index=4)

weather = download_weather(area, year)
st.caption(f"Hourly ERA5 reanalysis from open-meteo, averaged over 20 random locations in {area} "
           f"in {year}. All times are in UTC. Change the area in the sidebar.")

variables = list(LABELS.keys()) 
tab_spc, tab_lof = st.tabs(["Outliers (SPC)", "Anomalies (LOF)"]) #st.tabs lager de to fanene.

# ---------- Fane 1: SPC ----------
with tab_spc:
    col1, col2, col3 = st.columns(3)
    # key gjør at variabelvalget i hver fane er uavhengig av det andre.
    column = col1.selectbox("Variable:", variables, index=variables.index("precipitation"),
                            format_func=LABELS.get, key="spc_variable")
    cutoff = col2.slider("DCT frequency cut-off", 10, 400, 100, step=10)
    n_std = col3.slider("Number of robust standard deviations", 1.0, 6.0, 3.0, step=0.5)

    # Forklarer cut-off i dager: indeks k svarer til k/2 svingninger i løpet av perioden.
    days = 2 * len(weather) / cutoff / 24
    st.caption(f"Variations slower than about {days:.0f} days are treated as seasonal and removed "
               "before the limits are calculated.")

    fig, summary, outliers = spc_outliers(weather, column, cutoff=cutoff, n_std=n_std)
    st.pyplot(fig)
    plt.close(fig)   # frigjør minne, siden siden tegnes på nytt ved hvert klikk.

    # Oppsummering som nøkkeltall (stor forbokstav, resten som før, så "SD (SATV)" beholdes).
    for col, (label, value) in zip(st.columns(len(summary)), summary.items()):
        col.metric(label[0].upper() + label[1:], value) #metric viser nøkkeltallene

    # Tabellen med uteliggerne i en utvidbar boks: lesbar tid, kolonnenavn med enhet og to desimaler.
    with st.expander("Show outliers"):
        st.dataframe(
            outliers,
            column_config={
                "_index": st.column_config.DatetimeColumn("Time (UTC)", format="YYYY-MM-DD HH:mm"),
                column: st.column_config.NumberColumn(LABELS[column], format="%.2f"), 
            }, 
            width="stretch",
        ) 

# ---------- Fane 2: LOF ----------
with tab_lof:
    col1, col2, col3 = st.columns(3)
    column = col1.selectbox("Variable:", variables, index=variables.index("temperature_2m"),
                            format_func=LABELS.get, key="lof_variable")
    contamination_pct = col2.slider("Proportion of anomalies (%)", 0.1, 10.0, 1.0, step=0.1)
    n_neighbors = col3.slider("Number of neighbours", 5, 100, 20, step=5)

    fig, summary, anomalies = lof_anomalies(weather, column,
                                            contamination=contamination_pct / 100,
                                            n_neighbors=n_neighbors)
    st.pyplot(fig)
    plt.close(fig)

    # Oppsummering som nøkkeltall.
    for col, (label, value) in zip(st.columns(len(summary)), summary.items()):
        col.metric(label[0].upper() + label[1:], value)

    # Tabellen med anomaliene, formatert på samme måte som i SPC-fanen.
    with st.expander("Show anomalies"):
        st.dataframe(
            anomalies,
            column_config={
                "_index": st.column_config.DatetimeColumn("Time (UTC)", format="YYYY-MM-DD HH:mm"),
                column: st.column_config.NumberColumn(LABELS[column], format="%.2f"),
            },
            width="stretch",
        )