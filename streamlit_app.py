import streamlit as st
import pandas as pd
import altair as alt

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(page_title="Mehiläinen Kela-korvaukset", layout="wide")
st.title("🏥 Mehiläisen Kela-korvaukset (2011–2014)")

# -----------------------------
# LOAD DATA
# -----------------------------
URL = "https://gist.githubusercontent.com/SanteriKorhonen/f98eb53a97e0108d5bc78c17e55dc169/raw/e831683e187130a7dd908cb3cb0dd824c7dadb3f/sairaanhoidon-suorakorvaukset-palveluntuottajittain-v-2011-2014"

@st.cache_data
def load_data(url):
    return pd.read_csv(
        url,
        sep=";",
        encoding="latin1",
        engine="python",
        on_bad_lines="skip"
    )

df = load_data(URL)

# -----------------------------
# CLEAN COLUMNS
# -----------------------------
# Drop unnamed columns
df = df.loc[:, ~df.columns.str.startswith("Unnamed")]

# Normalize column names
df.columns = (
    df.columns
    .str.strip()
    .str.lower()
    .str.replace(" ", "_")
    .str.replace("ä", "a")
    .str.replace("ö", "o")
)

# -----------------------------
# SELECT RELEVANT COLUMNS
# -----------------------------
provider_col = "palveluntuottaja" if "palveluntuottaja" in df.columns else df.columns[0]
year_col = "vuosi" if "vuosi" in df.columns else df.columns[1]
amount_col = "korvaus" if "korvaus" in df.columns else df.columns[2]

# -----------------------------
# TYPE CLEANING
# -----------------------------
df[year_col] = pd.to_numeric(df[year_col], errors="coerce")

df[amount_col] = (
    df[amount_col]
    .astype(str)
    .str.replace(r"[^\d,.-]", "", regex=True)
    .str.replace(",", ".", regex=False)
)
df[amount_col] = pd.to_numeric(df[amount_col], errors="coerce")

df = df.dropna(subset=[year_col, amount_col])

# -----------------------------
# FILTER FOR MEHILÄINEN AND YEARS 2011–2014
# -----------------------------
df_mehilainen = df[
    (df[provider_col].str.contains("Mehiläinen", case=False)) &
    (df[year_col].between(2011, 2014))
]

# -----------------------------
# AGGREGATE BY YEAR
# -----------------------------
year_df = (
    df_mehilainen
    .groupby(year_col, as_index=False)[amount_col]
    .sum()
    .sort_values(year_col)
)

# -----------------------------
# SHOW TABLE
# -----------------------------
st.subheader("📊 Korvaukset vuosittain")
st.dataframe(year_df, use_container_width=True)

# -----------------------------
# BAR CHART
# -----------------------------
bar = (
    alt.Chart(year_df)
    .mark_bar(color="#1f77b4")
    .encode(
        x=alt.X(f"{year_col}:O", title="Vuosi"),
        y=alt.Y(f"{amount_col}:Q", title="Korvaus (€)"),
        tooltip=[year_col, amount_col]
    )
    .properties(height=400)
)

st.altair_chart(bar, use_container_width=True)

# -----------------------------
# PIE CHART
# -----------------------------
pie = (
    alt.Chart(year_df)
    .mark_arc(innerRadius=50)
    .encode(
        theta=alt.Theta(f"{amount_col}:Q"),
        color=alt.Color(f"{year_col}:N", legend=None),
        tooltip=[year_col, amount_col]
    )
    .properties(height=400)
)

st.altair_chart(pie, use_container_width=True)
