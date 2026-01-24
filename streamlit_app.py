import streamlit as st
import pandas as pd
import altair as alt

# --------------------------------------------------
# Page setup
# --------------------------------------------------
st.set_page_config(
    page_title="Sairaanhoidon suorakorvaukset",
    page_icon="🏥",
    layout="wide"
)

st.title("🏥 Sairaanhoidon suorakorvaukset 2011–2014")
st.write(
    """
    Visualisointi suomalaisesta sairaanhoidon suorakorvausdatasta.
    Data sisältää epäsäännöllisiä rivejä, jotka käsitellään turvallisesti.
    """
)

# --------------------------------------------------
# RAW CSV URL (CONFIRMED)
# --------------------------------------------------
URL = (
    "https://gist.githubusercontent.com/SanteriKorhonen/"
    "f98eb53a97e0108d5bc78c17e55dc169/raw/"
    "e831683e187130a7dd908cb3cb0dd824c7dadb3f/"
    "sairaanhoidon-suorakorvaukset-palveluntuottajittain-v-2011-2014"
)

# --------------------------------------------------
# Load data (ROBUST MODE)
# --------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv(
        URL,
        sep=";",
        encoding="latin1",
        engine="python",
        on_bad_lines="skip"
    )
    return df

df = load_data()

st.success("CSV ladattu onnistuneesti ✅")

# --------------------------------------------------
# Show raw data
# --------------------------------------------------
with st.expander("📄 Näytä raakadata"):
    st.dataframe(df, use_container_width=True)

# --------------------------------------------------
# Clean column names
# --------------------------------------------------
df.columns = (
    df.columns
    .str.strip()
    .str.lower()
    .str.replace(" ", "_")
    .str.replace("ä", "a")
    .str.replace("ö", "o")
)

# --------------------------------------------------
# Identify columns safely
# --------------------------------------------------
provider_col = [c for c in df.columns if "palvelu" in c][0]
year_col = [c for c in df.columns if "vuosi" in c][0]
amount_col = [c for c in df.columns if "korvaus" in c][0]

# --------------------------------------------------
# Convert types
# --------------------------------------------------
df[year_col] = pd.to_numeric(df[year_col], errors="coerce")

df[amount_col] = (
    df[amount_col]
    .astype(str)
    .str.replace(",", ".", regex=False)
    .str.replace(" ", "", regex=False)
)

df[amount_col] = pd.to_numeric(df[amount_col], errors="coerce")

df = df.dropna(subset=[year_col, amount_col])

# --------------------------------------------------
# Sidebar filters
# --------------------------------------------------
st.sidebar.header("🔎 Suodattimet")

providers = st.sidebar.multiselect(
    "Palveluntuottaja",
    sorted(df[provider_col].unique()),
    default=sorted(df[provider_col].unique())[:5]
)

years = st.sidebar.slider(
    "Vuodet",
    int(df[year_col].min()),
    int(df[year_col].max()),
    (2011, 2014)
)

# --------------------------------------------------
# Filter & aggregate
# --------------------------------------------------
filtered = df[
    df[provider_col].isin(providers)
    & df[year_col].between(years[0], years[1])
]

summary = (
    filtered
    .groupby([year_col, provider_col])[amount_col]
    .sum()
    .reset_index()
)

# --------------------------------------------------
# Table
# --------------------------------------------------
st.subheader("📊 Yhteenveto")
st.dataframe(summary, use_container_width=True)

# --------------------------------------------------
# Chart
# --------------------------------------------------
st.subheader("📈 Korvaukset vuosittain")

chart = (
    alt.Chart(summary)
    .mark_line(point=True)
    .encode(
        x=alt.X(f"{year_col}:O", title="Vuosi"),
        y=alt.Y(f"{amount_col}:Q", title="Korvaus (€)"),
        color=alt.Color(f"{provider_col}:N", title="Palveluntuottaja"),
        tooltip=[year_col, provider_col, amount_col]
    )
    .properties(height=400)
)

st.altair_chart(chart, use_container_width=True)
