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

# Velger én sammenhengende dataserie og sorterer etter dato
df_area1 = df[
    (df["area_type"] == "EL") & (df["area_number"] == 1)
].sort_values("date")

# Finner den første kalendermåneden i dataserien
first_period = df_area1["date"].dt.to_period("M").min()
first_month = df_area1[df_area1["date"].dt.to_period("M") == first_period]

# Alle datakolonnene vises som rader. Date brukes som tidsakse.
all_columns = [
    "area_type",
    "area_number",
    "year",
    "week",
    "fill_level",
    "capacity_twh",
    "stored_energy_twh",
    "next_publication_date",
    "previous_week_fill_level",
    "change_in_fill_level",
]

table_rows = []

for col in all_columns:
  if col in df_area1.columns:
    # Sjekker om kolonnen er numerisk for å hente ut linjegraf-data
    is_numeric = pd.api.types.is_numeric_dtype(df_area1[col])

    if is_numeric:
      chart_data = first_month[col].dropna().tolist()
    else:
      chart_data = []  # Tom liste for tekst- og datokolonner

    table_rows.append({
        "Variable": col,
        "First month": chart_data,
    })

summary_df = pd.DataFrame(table_rows)

st.write(
    "Each row represents one data column. The date column is used as the "
    "time axis. The mini charts show the first month for numerical series."
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