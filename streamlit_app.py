# app.py
import io
import os
import altair as alt
import pandas as pd
import streamlit as st
import requests

# ------------------------------
# Put your original URL here:
# (I left it exactly as in your message)
url = "https://gist.githubusercontent.com/SanteriKorhonen/f98eb53a97e0108d5bc78c17e55dc169/raw/e831683e187130a7dd908cb3cb0dd824c7dadb3f/sairaanhoidon-suorakorvaukset-palveluntuottajittain-v-2011-2014"
# ------------------------------

# Optional: create a simple Streamlit theme config file so the app uses a consistent theme.
# (If you already set a theme in .streamlit/config.toml or in deployment, you can remove this.)
def ensure_streamlit_theme():
    cfg_dir = ".streamlit"
    os.makedirs(cfg_dir, exist_ok=True)
    cfg_path = os.path.join(cfg_dir, "config.toml")
    # Only write if not present (so we don't overwrite an existing custom config)
    if not os.path.exists(cfg_path):
        cfg = """
[theme]
base="dark"
primaryColor="#1f77b4"
backgroundColor="#0e1117"
secondaryBackgroundColor="#111317"
textColor="#fafafa"
font="sans serif"
"""
        with open(cfg_path, "w", encoding="utf-8") as f:
            f.write(cfg)

# Try to ensure theme (non-destructive)
try:
    ensure_streamlit_theme()
except Exception:
    # If writing files is not allowed in your environment (some deploys), ignore silently.
    pass


st.set_page_config(page_title="Movies dataset (from your CSV)", page_icon="🎬")
st.title("🎬 Movies dataset — from your CSV")

st.write(
    """
    This app uses **your CSV URL** (the `url` variable at the top of this file).
    The app will try to read that URL directly. If it fails, it will attempt a common
    transformation for GitHub Gist links to try to find the raw CSV. If both fail,
    follow the instructions printed below to provide a raw CSV URL or upload a file.
    """
)

@st.cache_data
def load_data_from_url(url_to_try):
    """
    Try reading the CSV from the provided URL. If direct read fails, attempt
    to convert a Gist URL to a raw-content URL (best-effort). Returns pd.DataFrame
    or raises an informative exception.
    """
    # 1) try direct read
    try:
        df = pd.read_csv(url_to_try)
        return df
    except Exception as e_direct:
        direct_exc = e_direct

    # 2) if URL looks like a gist.github.com link, attempt to turn it into a raw URL
    # This is a best-effort: gist raw URLs usually look like:
    #  https://gist.githubusercontent.com/<user>/<gist-id>/raw/<filename>
    # We can't guess <user> or <filename> reliably, but we can attempt one transformation:
    try:
        if "gist.github.com" in url_to_try:
            # Remove trailing .git if present
            u = url_to_try.rstrip("/")
            if u.endswith(".git"):
                u = u[:-4]
            # Attempt to convert domain
            # NOTE: this guess will not always work; if your gist has multiple files,
            # or a username, this might still fail.
            u2 = url_to_try.replace("gist.github.com", "gist.githubusercontent.com")
            # if original ended with .git, replace that too
            u2 = u2.rstrip(".git")
            # Append "/raw" at the end (very rough)
            if not u2.endswith("/raw"):
                u2 = u2 + "/raw"
            try:
                df = pd.read_csv(u2)
                return df
            except Exception:
                pass  # fall-through to final error
    except Exception:
        pass

    # 3) final: try using requests to fetch text and read via pd.read_csv on buffer
    try:
        r = requests.get(url_to_try, timeout=10)
        r.raise_for_status()
        text = r.text
        df = pd.read_csv(io.StringIO(text))
        return df
    except Exception as e_requests:
        # Raise a combined error so the UI can show helpful info
        raise RuntimeError(
            "Failed to read CSV.\n"
            f"- Direct read error: {direct_exc}\n"
            f"- Requests read error: {e_requests}\n\n"
            "If this is a GitHub Gist link, please provide the raw file URL (click 'Raw' on the gist file and copy that link),\n"
            "or upload the CSV using the file uploader below."
        )


# Try to load data
df = None
load_error = None
try:
    df = load_data_from_url(url)
except Exception as e:
    load_error = str(e)

# If loading failed, show error and provide uploader
if df is None:
    st.error("Could not load CSV from the provided URL.")
    st.write("Details / troubleshooting:")
    st.code(load_error or "Unknown error")
    st.write(
        """
        **How to get a raw CSV link from a GitHub Gist**
        1. Open the gist page in your browser.
        2. Click the filename you want to download so the file content is displayed.
        3. Click the **Raw** button (top-right of the file view) — that will open a raw file URL.
        4. Copy that raw URL and paste it into the `url` variable in this script, or paste it into the uploader below.
        """
    )
    uploaded = st.file_uploader("Or upload a CSV file here", type=["csv"])
    if uploaded is not None:
        try:
            df = pd.read_csv(uploaded)
            st.success("CSV uploaded and loaded successfully.")
        except Exception as e:
            st.error(f"Uploaded file could not be parsed as CSV: {e}")

# If we have a dataframe, show the rest of the app (mirrors your ready code)
if df is not None:
    st.write("### Raw data (first 5 rows)")
    st.dataframe(df.head())

    # Try to detect useful columns for the movie example. If your CSV has different column names,
    # we attempt to adapt gracefully.
    # Expected columns in 'ready code' were: 'genre', 'year', 'gross'
    cols = [c.lower() for c in df.columns]
    # find candidate column names
    genre_col = None
    year_col = None
    gross_col = None

    for c in df.columns:
        lower = c.lower()
        if "genre" in lower and genre_col is None:
            genre_col = c
        if ("year" in lower or "release" in lower) and year_col is None:
            year_col = c
        if ("gross" in lower or "revenue" in lower or "box" in lower) and gross_col is None:
            gross_col = c

    # If any required columns missing, show a helpful message and let the user pick columns
    if genre_col is None or year_col is None or gross_col is None:
        st.warning("Could not automatically find 'genre', 'year', and 'gross' columns in your CSV.")
        st.write("Please map columns manually (choose the column that corresponds to each):")
        genre_col = st.selectbox("Genre column", options=["(none)"] + list(df.columns), index=0)
        year_col = st.selectbox("Year column", options=["(none)"] + list(df.columns), index=0)
        gross_col = st.selectbox("Gross column", options=["(none)"] + list(df.columns), index=0)

        if "(none)" in (genre_col, year_col, gross_col):
            st.error("You must pick a column for genre, year, and gross to continue.")
            st.stop()

    # Ensure year column is numeric
    try:
        df[year_col] = pd.to_numeric(df[year_col], errors="coerce").astype("Int64")
    except Exception:
        pass

    # Basic cleaning: drop rows with missing year or genre
    df_clean = df.dropna(subset=[genre_col, year_col])

    # Convert gross to numeric (if possible)
    try:
        df_clean[gross_col] = pd.to_numeric(df_clean[gross_col].astype(str).str.replace(r"[^0-9.\-]", "", regex=True), errors="coerce").fillna(0)
    except Exception:
        pass

    # Show a multiselect for genres
    genres = st.multiselect(
        "Genres",
        sorted(df_clean[genre_col].astype(str).unique()),
        sorted(df_clean[genre_col].astype(str).unique())[:6],  # pick first 6 as default
    )

    # Year slider bounds based on data
    min_year = int(df_clean[year_col].min())
    max_year = int(df_clean[year_col].max())
    years = st.slider("Years", min_year, max_year, (min_year, max_year))

    # Filter, pivot, and display like your ready code
    df_filtered = df_clean[
        (df_clean[genre_col].isin(genres)) & (df_clean[year_col].between(years[0], years[1]))
    ] if genres else df_clean[df_clean[year_col].between(years[0], years[1])]

    # Aggregate gross by year and genre
    df_agg = df_filtered.groupby([year_col, genre_col])[gross_col].sum().reset_index()
    df_pivot = df_agg.pivot_table(index=year_col, columns=genre_col, values=gross_col, aggfunc="sum", fill_value=0)
    df_pivot = df_pivot.sort_index(ascending=False)

    st.write("### Aggregated table (gross by year & genre)")
    # Display. If year is index, show as column for st.dataframe clarity
    st.dataframe(df_pivot.reset_index(), use_container_width=True)

    # Prepare chart
    df_chart = pd.melt(df_pivot.reset_index(), id_vars=year_col, var_name="genre", value_name="gross")
    # Convert year to string for Altair categorical x axis
    df_chart[str(year_col)] = df_chart[year_col].astype(str)

    chart = (
        alt.Chart(df_chart)
        .mark_line(point=True)
        .encode(
            x=alt.X(f"{str(year_col)}:N", title="Year"),
            y=alt.Y("gross:Q", title="Gross earnings ($)"),
            color=alt.Color("genre:N", title="Genre"),
            tooltip=[str(year_col), "genre", "gross"]
        )
        .properties(height=400)
    )

    st.altair_chart(chart, use_container_width=True)
