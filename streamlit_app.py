import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Sairaanhoidon korvaukset", layout="wide")
st.title("🏥 Sairaanhoidon suorakorvaukset")

# -----------------------------
# LOAD DATA
# -----------------------------
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

# -----------------------------
# CLEAN COLUMNS
# -----------------------------
# Drop Unnamed columns (4–7 and any others)
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

st.expander("📄 Raw columns").write(list(df.columns))

# -----------------------------
# SAFE COLUMN SELECTION
# -----------------------------
st.sidebar.header("⚙️ Column mapping")

def guess_col(keywords):
    for c in df.columns:
        for k in keywords:
            if k in c:
                return c
    return None

provider_guess = guess_col(["palvelu", "tuottaja"])
year_guess = guess_col(["vuosi"])
amount_guess = guess_col(["korva", "euro", "summa", "maara"])

provider_col = st.sidebar.selectbox(
    "Palveluntuottaja",
    df.columns,
    index=df.columns.get_loc(provider_guess) if provider_guess else 0
)

year_col = st.sidebar.selectbox(
    "Vuosi",
    df.columns,
    index=df.columns.get_loc(year_guess) if year_guess else 0
)

amount_col = st.sidebar.selectbox(
    "Korvaus (€)",
    df.columns,
    index=df.columns.get_loc(amount_guess) if amount_guess else 0
)

# -----------------------------
# TYPE CLEANING
# -----------------------------
df = df.copy()

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
# FILTERS
# -----------------------------
years = sorted(df[year_col].unique())
year = st.sidebar.selectbox("Select year", years)

# -----------------------------
# AGGREGATE
# -----------------------------
year_df = (
    df[df[year_col] == year]
    .groupby(provider_col, as_index=False)[amount_col]
    .sum()
    .sort_values(amount_col, ascending=False)
)

st.subheader(f"📊 Korvaukset vuonna {int(year)}")
st.dataframe(year_df, use_container_width=True)

# -----------------------------
# BAR CHART
# -----------------------------
bar = (
    alt.Chart(year_df)
    .mark_bar()
    .encode(
        x=alt.X(f"{provider_col}:N", sort="-y", title="Palveluntuottaja"),
        y=alt.Y(f"{amount_col}:Q", title="Korvaus (€)"),
        tooltip=[provider_col, amount_col]
    )
    .properties(height=400)
)

st.altair_chart(bar, use_container_width=True)

# -----------------------------
# PIE CHART
# -----------------------------
pie = (
    alt.Chart(year_df)
    .mark_arc()
    .encode(
        theta=alt.Theta(f"{amount_col}:Q"),
        color=alt.Color(f"{provider_col}:N"),
        tooltip=[provider_col, amount_col]
    )
    .properties(height=400)
)

st.altair_chart(pie, use_container_width=True)
