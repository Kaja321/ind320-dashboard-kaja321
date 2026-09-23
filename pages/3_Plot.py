import pandas as pd
import plotly.express as px
import streamlit as st

st.title("Interactive Reservoir Data Visualization")


# Les inn data med caching for god app-ytelse
@st.cache_data
def load_data():
    df = pd.read_csv("reservoirs.csv")

    # Omdøper kolonnene til engelske og forståelige navn
    df = df.rename(
        columns={
            "dato_Id": "date",
            "omrType": "area_type",
            "omrnr": "area_number",
            "iso_aar": "year",
            "iso_uke": "week",
            "fyllingsgrad": "fill_level",
            "kapasitet_TWh": "capacity_twh",
            "fylling_TWh": "stored_energy_twh",
            "neste_Publiseringsdato": "next_publication_date",
            "fyllingsgrad_forrige_uke": "previous_week_fill_level",
            "endring_fyllingsgrad": "change_in_fill_level",
        }
    )

    df["date"] = pd.to_datetime(df["date"])
    return df


df = load_data()

# Filtrer på område EL 1 for å få én sammenhengende tidsserie
df_area1 = df[
    (df["area_type"] == "EL") & (df["area_number"] == 1)
].sort_values("date")

# Oppretter en hjelpekolonne med år og måned
df_area1["year_month"] = df_area1["date"].dt.to_period("M").astype(str)

# Henter månedene i kronologisk rekkefølge
months = df_area1["year_month"].unique().tolist()

st.sidebar.header("Plot Controls")

# Alle kolonnene fra CSV-filen, unntatt datoen som brukes som x-akse
# og year_month som bare er en hjelpekolonne
all_csv_columns = [
    col
    for col in df_area1.columns
    if col not in ["date", "year_month"]
]

# Velg én enkelt kolonne eller alle kolonnene
selected_col = st.sidebar.selectbox(
    "Select column / variable:",
    options=["All columns"] + all_csv_columns,
)

# Velg en delmengde av månedene
# Begge endene står på første måned som standard
if months:
    selected_period = st.sidebar.select_slider(
        "Select period:",
        options=months,
        value=(months[0], months[0]),
    )

    start_month, end_month = selected_period

    df_display = df_area1[
        (df_area1["year_month"] >= start_month)
        & (df_area1["year_month"] <= end_month)
    ]
else:
    start_month = "No data"
    end_month = "No data"
    df_display = df_area1

# Numeriske kolonner brukes når alle kolonnene skal vises sammen
# Tekst- og datokolonner kan fortsatt velges enkeltvis
numeric_cols = (
    df_display[all_csv_columns]
    .select_dtypes(include="number")
    .columns.tolist()
)

st.subheader(f"Displaying data from {start_month} to {end_month}")

# Lager det interaktive plottet
if selected_col == "All columns":
    fig = px.line(
        df_display,
        x="date",
        y=numeric_cols,
        title=(
            f"Comparison of all numeric columns "
            f"({start_month} to {end_month})"
        ),
        labels={
            "date": "Date",
            "value": "Value",
            "variable": "Variable",
        },
    )
else:
    fig = px.line(
        df_display,
        x="date",
        y=selected_col,
        title=(
            f"Development of {selected_col} "
            f"({start_month} to {end_month})"
        ),
        labels={
            "date": "Date",
            selected_col: selected_col,
        },
    )

# Viser plottet i Streamlit
st.plotly_chart(fig, use_container_width=True)