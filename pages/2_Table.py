import pandas as pd
import streamlit as st

st.title("Reservoir Data Overview")


# Leser inn data med caching for bedre ytelse
@st.cache_data
def load_data():
    df = pd.read_csv("reservoirs.csv")

    df = df.rename(
        columns={
            "dato_Id": "date",
            "omrType": "area_type",
            "omrnr": "area_number",
            "fyllingsgrad": "fill_level",
            "kapasitet_TWh": "capacity_twh",
            "fylling_TWh": "stored_energy_twh",
            "endring_fyllingsgrad": "change_in_fill_level",
        }
    )

    df["date"] = pd.to_datetime(df["date"])
    return df


df = load_data()

# Velger én sammenhengende dataserie og sorterer etter dato
df_area1 = df[
    (df["area_type"] == "EL") & (df["area_number"] == 1)
].sort_values("date")

# Finner den første kalendermåneden i dataserien
first_period = df_area1["date"].dt.to_period("M").min()

first_month = df_area1[
    df_area1["date"].dt.to_period("M") == first_period
]

# Variablene som skal vises som dataserier
numeric_cols = [
    "fill_level",
    "stored_energy_twh",
    "capacity_twh",
    "change_in_fill_level",
]

# Lager én rad per variabel
table_rows = []

for column in numeric_cols:
    table_rows.append(
        {
            "Variable": column,
            "First month": first_month[column].dropna().tolist(),
            "Latest value": df_area1[column].iloc[-1],
        }
    )

summary_df = pd.DataFrame(table_rows)

st.write(
    "Each row represents one data series. The mini charts show "
    "the development during the first month."
)

st.dataframe(
    summary_df,
    column_config={
        "First month": st.column_config.LineChartColumn(
            "First month trend",
            width="medium",
            help="Development during the first month of the data series",
        )
    },
    use_container_width=True,
    hide_index=True,
)