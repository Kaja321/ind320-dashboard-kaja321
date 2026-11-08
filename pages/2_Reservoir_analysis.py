# Side 2: Analyse av fyllingsgraden for valgt område.
# Fane 1: STL-dekomponering. Fane 2: spektrogram.
# Området velges i sidebaren (felles for alle sidene), parameterne velges lokalt i hver fane.
import matplotlib.pyplot as plt
import streamlit as st
from functions import area_selector, load_reservoirs, stl_plot, spectrogram_plot

st.set_page_config(layout="wide")
st.title("Reservoir Analysis")

area = area_selector()
reservoirs = load_reservoirs()
st.write(f"Weekly fill level for **{area}** from NVE. Change the area in the sidebar.")

tab_stl, tab_spec = st.tabs(["STL decomposition", "Spectrogram"])

# ---------- Fane 1: STL ----------
with tab_stl:
    st.write("STL splits the fill level into a long-term **trend**, a **seasonal** pattern "
             "that repeats every year, and a **residual** (deviations from a normal year).")
    col1, col2, col3 = st.columns(3)
    # Begge glatterne må være oddetall, derfor step=2 fra et oddetall
    seasonal = col1.slider("Seasonal smoother", 7, 51, 13, step=2,
                           help="Higher values give a seasonal pattern that changes more slowly")
    trend = col2.slider("Trend smoother (weeks)", 53, 261, 105, step=2,
                        help="Must be larger than one year (52 weeks)")
    robust = col3.checkbox("Robust", value=False,
                           help="Makes trend and season less sensitive to extreme weeks")

    fig = stl_plot(reservoirs, area, seasonal=seasonal, trend=trend, robust=robust)
    st.pyplot(fig)
    plt.close(fig)   # frigjør minne, siden siden tegnes på nytt ved hvert klikk

# ---------- Fane 2: spektrogram ----------
with tab_spec:
    st.write("The spectrogram shows how strong each cycle is over time. "
             "The band at **1 cycle per year** is the yearly filling and emptying of the reservoirs.")
    col1, col2 = st.columns(2)
    window_length = col1.slider("Window length (weeks)", 26, 260, 104, step=26)
    # Overlappet velges i prosent, så det alltid blir mindre enn vinduet
    overlap_pct = col2.slider("Window overlap (%)", 0, 90, 75, step=5)
    overlap = int(window_length * overlap_pct / 100)

    fig = spectrogram_plot(reservoirs, area, window_length=window_length, overlap=overlap)
    st.pyplot(fig)
    plt.close(fig)
    st.caption("Longer windows give sharper frequencies, shorter windows show changes over time better.")