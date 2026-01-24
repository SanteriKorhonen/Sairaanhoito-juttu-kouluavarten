# app.py
import streamlit as st
import pandas as pd
import altair as alt

# ------------------------
# Page config
# ------------------------
st.set_page_config(page_title="Sairaanhoidon suorakorvaukset", page_icon="🏥", layout="wide")
st.title("🏥 Sairaanhoidon suorakorvaukset 2011–2014")
st.write("Robust CSV loader + line, bar and pie charts. (Handles latin1 encoding, semicolon sep, messy rows.)")

# ------------------------
# Source URL (raw gist)
# ------------------------
URL = (
    "https://gist.githubusercontent.com/SanteriKorhonen/"
    "f98eb53a97e0108d5bc78c17e55dc169/raw/"
    "e831683e187130a7dd908cb3cb0dd824c7dadb3f/"
    "sairaanhoidon-suorakorvaukset-palveluntuottajittain-v-2011-2014"
)

# ------------------------
# Load function (robust)
# ------------------------
@st.cache_data
def load_from_url(url: str):
    """
    Try to read CSV directly. Use python engine and skip bad lines so the app doesn't crash on malformed rows.
    """
    try:
        df = pd.read_csv(url, sep=";", encoding="latin1", engine="python", on_bad_lines="skip")
        return df, None
    except Exception as e:
        return None, str(e)

# Try to load from URL
df, load_err = load_from_url(URL)

# If loading failed, allow upload
if df is None:
    st.error("CSV lataus URL:stä epäonnistui.")
    st.write("Virheilmoitus:")
    st.code(load_err)
    st.write("Voit ladata CSV:n manuaalisesti (esim. jos tiedosto on yksityinen tai URL ei toimi).")
    uploaded = st.file_uploader("Upload CSV (optional fallback)", type=["csv"])
    if uploaded is not None:
        try:
            # same parsing strategy for uploaded file
            df = pd.read_csv(uploaded, sep=";", encoding="latin1", engine="python", on_bad_lines="skip")
            st.success("Tiedosto ladattu paikallisesta uploadista.")
        except Exception as e:
            st.error("Uploaded file could not be parsed.")
            st.exception(e)
            st.stop()
    else:
        st.stop()
else:
    st.success("CSV ladattu URL:stä onnistuneesti ✅")

# ------------------------
# Remove Unnamed columns (Unnamed: 4 - Unnamed: 7 or any Unnamed)
# ------------------------
df = df.loc[:, ~df.columns.str.startswith("Unnamed")]

# Also drop fully-empty columns (if any)
df = df.dropna(axis=1, how="all")

# Show columns and first rows for transparency
with st.expander("📄 Raakadata (esikatselu)"):
    st.write("Sarakkeet:")
    st.code(list(df.columns))
    st.write("Ensimmäiset rivit:")
    st.dataframe(df.head(), use_container_width=True)

# ------------------------
# Clean column names to easier form
# ------------------------
clean_cols = (
    df.columns
    .str.strip()
    .str.lower()
    .str.replace(" ", "_")
    .str.replace("ä", "a")
    .str.replace("ö", "o")
    .str.replace("å", "a")
)
df.columns = clean_cols

# ------------------------
# Auto-detect likely columns (best-effort)
# ------------------------
def find_column(dfcols, keywords):
    for k in keywords:
        for c in dfcols:
            if k in c:
                return c
    return None

provider_col = find_column(df.columns, ["palvelu", "tuottaja", "provider", "yritys", "toimija"])
year_col = find_column(df.columns, ["vuosi", "year", "v"])
amount_col = find_column(df.columns, ["korva", "euro", "summa", "maara", "amount", "sum"])

# ------------------------
# Manual mapping fallback in sidebar (no crash)
# ------------------------
st.sidebar.header("⚙️ Sarakkeiden valinta / Column mapping")

if provider_col is None:
    provider_col = st.sidebar.selectbox("Valitse palveluntuottaja-sarake", options=list(df.columns), index=0)
else:
    provider_col = st.sidebar.selectbox("Valitse palveluntuottaja-sarake", options=list(df.columns), index=list(df.columns).index(provider_col))

if year_col is None:
    year_col = st.sidebar.selectbox("Valitse vuosi-sarake", options=list(df.columns), index=0)
else:
    year_col = st.sidebar.selectbox("Valitse vuosi-sarake", options=list(df.columns), index=list(df.columns).index(year_col))

if amount_col is None:
    amount_col = st.sidebar.selectbox("Valitse euromäärä-sarake", options=list(df.columns), index=0)
else:
    amount_col = st.sidebar.selectbox("Valitse euromäärä-sarake", options=list(df.columns), index=list(df.columns).index(amount_col))

st.sidebar.markdown("---")

# ------------------------
# Convert types and clean amount column
# ------------------------
# Make a defensive copy
df = df.copy()

# Year to numeric
df[year_col] = pd.to_numeric(df[year_col].astype(str).str.extract(r"(\d{4})", expand=False), errors="coerce")

# Clean amount: remove spaces and currency characters, replace comma with dot
def clean_amount_series(s):
    s2 = s.astype(str)
    s2 = s2.str.replace(r"[^\d,\-\.]", "", regex=True)   # keep digits, comma, dot, minus
    s2 = s2.str.replace(",", ".", regex=False)          # comma -> dot
    s2 = s2.str.replace(r"^\.$", "0", regex=True)       # edge-case single dot
    return pd.to_numeric(s2, errors="coerce")

df[amount_col] = clean_amount_series(df[amount_col])

# Drop rows missing year or amount
df = df.dropna(subset=[year_col, amount_col])

# Normalize provider column to string and strip
df[provider_col] = df[provider_col].astype(str).str.strip()

# ------------------------
# Filters: provider selection + year range
# ------------------------
st.sidebar.header("🔎 Suodattimet")
all_providers = sorted(df[provider_col].unique())
providers_default = all_providers[:6] if len(all_providers) > 6 else all_providers
selected_providers = st.sidebar.multiselect("Palveluntuottajat", options=all_providers, default=providers_default)

min_year = int(df[year_col].min())
max_year = int(df[year_col].max())
selected_years = st.sidebar.slider("Vuodet", min_year, max_year, (min_year, max_year))

# Option: top N for bar/pie charts
top_n = st.sidebar.number_input("Top N providers for charts (Other will be grouped)", min_value=3, max_value=50, value=10, step=1)

# ------------------------
# Apply filters and aggregate summary
# ------------------------
if selected_providers:
    filtered = df[(df[provider_col].isin(selected_providers)) & (df[year_col].between(selected_years[0], selected_years[1]))]
else:
    filtered = df[df[year_col].between(selected_years[0], selected_years[1])]

# Aggregated summary by year & provider
summary = (
    filtered
    .groupby([year_col, provider_col], observed=True)[amount_col]
    .sum()
    .reset_index()
    .sort_values([year_col, amount_col], ascending=[True, False])
)

st.subheader("📊 Yhteenveto (vuosi × palveluntuottaja)")
st.dataframe(summary, use_container_width=True)

# ------------------------
# Line chart (time series per provider)
# ------------------------
st.subheader("📈 Korvaukset vuosittain (viivakaavio)")

# Prepare data for line chart (pivot-like)
line_data = summary.copy()
line_data[year_col] = line_data[year_col].astype(int).astype(str)  # treat as categorical on x

line_chart = (
    alt.Chart(line_data)
    .mark_line(point=True)
    .encode(
        x=alt.X(f"{year_col}:N", title="Vuosi"),
        y=alt.Y(f"{amount_col}:Q", title="Korvaus (€)"),
        color=alt.Color(f"{provider_col}:N", title="Palveluntuottaja"),
        tooltip=[year_col, provider_col, amount_col]
    )
    .properties(height=350)
)
st.altair_chart(line_chart, use_container_width=True)

# ------------------------
# BAR CHART for a single year
# ------------------------
st.subheader("📊 Palveluntuottajat ja korvaukset (valittu vuosi)")

# Year selector for bar/pie
available_years = sorted(summary[year_col].unique())
if not available_years:
    st.info("Ei saatavilla olevia vuosiarvoja valinnoillasi.")
else:
    bar_year = st.selectbox("Valitse vuosi (bar & pie)", options=available_years, index=available_years.index(available_years[0]))

    # Data for chosen year
    bar_data = summary[summary[year_col] == bar_year].copy()
    # Sort descending by amount
    bar_data = bar_data.sort_values(amount_col, ascending=False)

    # Group smaller providers into "Other" if more than top_n
    if top_n and len(bar_data) > top_n:
        top = bar_data.head(top_n).copy()
        others = bar_data.tail(len(bar_data) - top_n)
        others_sum = others[amount_col].sum()
        top = pd.concat([top, pd.DataFrame({year_col: [bar_year], provider_col: ["Other"], amount_col: [others_sum]})], ignore_index=True)
        bar_plot_data = top
    else:
        bar_plot_data = bar_data

    # Bar chart
    bar_chart = (
        alt.Chart(bar_plot_data)
        .mark_bar()
        .encode(
            x=alt.X(f"{provider_col}:N", sort=alt.EncodingSortField(field=amount_col, op="sum", order="descending"), title="Palveluntuottaja"),
            y=alt.Y(f"{amount_col}:Q", title="Korvaus (€)"),
            tooltip=[provider_col, alt.Tooltip(f"{amount_col}:Q", format=",.2f")]
        )
        .properties(height=420)
    )

    st.altair_chart(bar_chart, use_container_width=True)

    # Optionally show the raw bar table
    with st.expander("Taulukko (valitun vuoden korvaukset)"):
        st.dataframe(bar_plot_data.reset_index(drop=True), use_container_width=True)

    # ------------------------
    # PIE CHART for the same year
    # ------------------------
    st.subheader("🥧 Korvausten jakautuminen (piirakkakaavio)")

    pie_data = bar_plot_data.copy()
    # If tiny or empty, show message
    if pie_data.empty:
        st.info("Ei dataa piirakkakaaviota varten valinnoillasi.")
    else:
        pie_chart = (
            alt.Chart(pie_data)
            .mark_arc(innerRadius=0)
            .encode(
                theta=alt.Theta(f"{amount_col}:Q", title="Korvaus (€)"),
                color=alt.Color(f"{provider_col}:N", title="Palveluntuottaja"),
                tooltip=[provider_col, alt.Tooltip(f"{amount_col}:Q", format=",.2f")]
            )
            .properties(height=420)
        )
        st.altair_chart(pie_chart, use_container_width=True)

# ------------------------
# Footer / extra options
# ------------------------
st.markdown("---")
col1, col2 = st.columns(2)
with col1:
    st.write(f"Rows in loaded data: **{len(df):,}**")
    st.write(f"Distinct providers: **{len(all_providers):,}**")
with col2:
    if st.button("Lataa puhdistettu CSV tästä"):
        # Prepare CSV bytes
        csv_bytes = summary.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", data=csv_bytes, file_name="suorakorvaukset-summary.csv", mime="text/csv")

st.caption("Huom: app käsittelee epämuodostuneita rivejä turvallisesti (skip). Muokkaa top N:ää jos piirakka näyttää liian täyteen.")
