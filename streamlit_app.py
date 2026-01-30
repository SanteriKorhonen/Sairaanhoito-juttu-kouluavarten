import streamlit as st
import pandas as pd
import altair as alt

# -------------------------------------------------
# PAGE SETUP
# -------------------------------------------------
st.set_page_config(
    page_title="Sairaanhoidon korvaukset",
    page_icon="🏥",
    layout="wide"
)

st.title("🏥 Sairaanhoidon suorakorvaukset (2011)")

st.write(
    """
    Tämä sovellus näyttää sairaanhoidon suorakorvaukset
    palveluntuottajittain vuonna 2011.
    """
)

# -------------------------------------------------
# LOAD DATA
# -------------------------------------------------
URL = "https://gist.githubusercontent.com/SanteriKorhonen/121b457471e9aff0c1a17d606d53e2ae/raw/12007ce1962d0160f2b92fa9264d29a7835fffec/sairaanhoidon-suorakorvaukset-palveluntuottajittain-v-2011.csv"

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

# -------------------------------------------------
# CLEAN DATA
# -------------------------------------------------
# Remove Unnamed columns
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

st.expander("📄 CSV sarakkeet").write(list(df.columns))

# -------------------------------------------------
# DEFINE CORRECT COLUMNS (IMPORTANT)
# -------------------------------------------------
provider_col = "palveluntuottaja"
amount_col = "korvaus_euroa"

# -------------------------------------------------
# CLEAN TYPES
# -------------------------------------------------
df[amount_col] = (
    df[amount_col]
    .astype(str)
    .str.replace(" ", "", regex=False)
    .str.replace(",", ".", regex=False)
)

df[amount_col] = pd.to_numeric(df[amount_col], errors="coerce")

df = df.dropna(subset=[provider_col, amount_col])

# -------------------------------------------------
# AGGREGATE DATA
# -------------------------------------------------
summary = (
    df
    .groupby(provider_col, as_index=False)[amount_col]
    .sum()
    .sort_values(amount_col, ascending=False)
)

st.subheader("📊 Korvaukset palveluntuottajittain (2011)")
st.dataframe(summary, use_container_width=True)

# -------------------------------------------------
# BAR CHART
# -------------------------------------------------
st.subheader("📊 Pylväsdiagrammi: Korvaukset palveluntuottajittain")

bar_chart = (
    alt.Chart(summary)
    .mark_bar()
    .encode(
        x=alt.X(f"{provider_col}:N", sort="-y", title="Palveluntuottaja"),
        y=alt.Y(f"{amount_col}:Q", title="Korvaus (€)"),
        tooltip=[provider_col, amount_col]
    )
    .properties(height=400)
)

st.altair_chart(bar_chart, use_container_width=True)

# -------------------------------------------------
# PIE CHART
# -------------------------------------------------
st.subheader("🥧 Piirakkakaavio: Korvausten jakautuminen")

pie_chart = (
    alt.Chart(summary)
    .mark_arc()
    .encode(
        theta=alt.Theta(f"{amount_col}:Q", title="Korvaus (€)"),
        color=alt.Color(f"{provider_col}:N", title="Palveluntuottaja"),
        tooltip=[provider_col, amount_col]
    )
    .properties(height=400)
)

st.altair_chart(pie_chart, use_container_width=True)
