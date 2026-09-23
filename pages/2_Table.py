# Side 2: Tabell som viser hver kolonne i datasettet som én rad,
# med en minigraf (LineChartColumn) for første måned av dataserien.
 
import pandas as pd
import streamlit as st

# Bruker hele bredden av nettleservinduet, slik at tabellen får mer plass
st.set_page_config(layout="wide")
 
st.title("Reservoir Data Overview")
 
 
# Leser inn data fra CSV-fila og gir kolonnene engelske navn.
# @st.cache_data gjør at fila bare leses én gang. Når brukeren bytter side
# eller endrer noe i appen, hentes dataene fra minnet i stedet for fra fila,
# slik at appen blir raskere.
@st.cache_data
def load_data():
    df = pd.read_csv("reservoirs.csv")
 
    # Omdøper kolonnene til engelske og forståelige navn (samme som i notebooken)
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
 
    # Gjør date om til datoformat, slik at vi kan sortere og hente ut måneder
    df["date"] = pd.to_datetime(df["date"])
    return df
 
 
df = load_data()
 
# Velger strømprisområde NO1 (area_type "EL" OG area_number 1) og sorterer etter dato.
# Begge må sjekkes, fordi nummer 1 også brukes av et annet område (VASS 1).
df_area1 = df[
    (df["area_type"] == "EL") & (df["area_number"] == 1)
].sort_values("date")
 
# Finner den første kalendermåneden i dataserien og plukker ut radene fra den måneden
first_period = df_area1["date"].dt.to_period("M").min()
first_month = df_area1[df_area1["date"].dt.to_period("M") == first_period]
 
# Alle datakolonnene skal vises som hver sin rad i tabellen.
# date er ikke med som egen rad, fordi den brukes som tidsakse i minigrafene.
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

 # Kort beskrivelse av hva hver kolonne inneholder, vises som egen kolonne i tabellen
descriptions = {
    "area_type": "Type area (EL = price area)",
    "area_number": "Area number (1 = NO1)",
    "year": "Year of the measurement",
    "week": "Week number of the measurement",
    "fill_level": "Share of reservoir capacity in use (0–1)",
    "capacity_twh": "Maximum energy the reservoirs can store (TWh)",
    "stored_energy_twh": "Energy currently stored in the reservoirs (TWh)",
    "next_publication_date": "Date of next data publication",
    "previous_week_fill_level": "Fill level the week before (0–1)",
    "change_in_fill_level": "Change in fill level from previous week",
}

# Bygger opp tabellen rad for rad: navnet på kolonnen og verdiene fra første måned
table_rows = []
 
for col in all_columns:
    # Sjekker om kolonnen inneholder tall. Bare tall kan vises som linjegraf.
    is_numeric = pd.api.types.is_numeric_dtype(df_area1[col])
 
    if is_numeric:
        # Henter verdiene fra første måned som en liste (én verdi per uke)
        chart_data = first_month[col].dropna().tolist()
    else:
        # Tekst- og datokolonner får en tom liste, og da vises ingen graf
        chart_data = []
 
    table_rows.append({
        "Variable": col,
        "Description": descriptions[col],
        "First month": chart_data,
    })
 
# Gjør lista med rader om til en tabell (DataFrame)
summary_df = pd.DataFrame(table_rows)
 
# Kort forklaring til brukeren over tabellen, med hvilken måned minigrafene viser
st.write(
    f"Each row represents one data column for price area NO1. "
    f"The mini charts show the development during the first month "
    f"of the data series ({first_period.strftime('%B %Y')}). "
    f"Text and date columns have no chart."
)
 
# st.dataframe viser tabellen i appen.
# column_config gjør "First month"-kolonnen om til små linjegrafer
# (LineChartColumn) i stedet for å vise listene som tekst.
st.dataframe(
    summary_df,
    column_config={
        "First month": st.column_config.LineChartColumn(
            "First month trend",
            width="large",
            help="Development during the first month of the data series",
        )
    },
    width="stretch",     # tabellen fyller hele bredden på siden
    hide_index=True,     # skjuler radnumrene til venstre
)