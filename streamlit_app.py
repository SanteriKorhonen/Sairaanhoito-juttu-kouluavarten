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
    "Tämä sovellus näyttää sairaanhoidon suorakorvaukset "
    "palveluntuottajittain vuonna 2011."
)

# -------------------------------------------------
# LOAD DATA (CORRECT FORMAT)
# -------------------------------------------------
URL = (
    "https://gist.githubusercontent.com/SanteriKorhonen/"
    "121b457471e9aff0c1a17d606d53e2ae/raw/"
    "12007ce1962d0160f2b92fa9264d29a7835fffec/"
    "sairaanhoidon-suorakorvaukset-palveluntuottajittain-v-2011.csv"
)

@st.cache_data
def load_data(url):
    return pd.read_csv(
        url,
        sep=",",
        encoding="latin1",
        header=None,
        names=[
            "y_tunnus",
            "palveluntuottaja",
            "korvaus_euroa",
            "vuosi"
        ]
    )

df = load_data(URL)

# -------------------------------------------------
# SHOW RAW DATA (REQUIRED BY YOU)
# -------------------------------------------------
st.subheader("📄 CSV sarakkeet")
st.code(list(df.columns))

st.subheader("📄 Raakadata (CSV)")
st.dataframe(df, use_container_width=True)

# -------------------------------------------------
# CLEAN DATA
# -------------------------------------------------
df["korvaus_euroa"] = (
    df["korvaus_euroa"]
    .astype(str)
    .str.replace('"', "", regex=False)
    .str.replace(",", ".", regex=False)
)

df["korvaus_euroa"] = pd.to_numeric(df["korvaus_euroa"], errors="coerce")
df["vuosi"] = pd.to_numeric(df["vuosi"], errors="coerce")

df = df.dropna(subset=["palveluntuottaja", "korvaus_euroa"])

# -------------------------------------------------
# AGGREGATE DATA
# -------------------------------------------------
summary = (
    df
    .groupby("palveluntuottaja", as_index=False)["korvaus_euroa"]
    .sum()
    .sort_values("korvaus_euroa", ascending=False)
)

# -------------------------------------------------
# SHOW AGGREGATED TABLE
# -------------------------------------------------
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
        x=alt.X(
            "palveluntuottaja:N",
            sort="-y",
            title="Palveluntuottaja"
        ),
        y=alt.Y(
            "korvaus_euroa:Q",
            title="Korvaus (€)"
        ),
        tooltip=["palveluntuottaja", "korvaus_euroa"]
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
        theta=alt.Theta(
            "korvaus_euroa:Q",
            title="Korvaus (€)"
        ),
        color=alt.Color(
            "palveluntuottaja:N",
            title="Palveluntuottaja"
        ),
        tooltip=["palveluntuottaja", "korvaus_euroa"]
    )
    .properties(height=400)
)

st.altair_chart(pie_chart, use_container_width=True)
