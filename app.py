import streamlit as st
import pandas as pd
from libsql_client import create_client_sync

# Connect to Turso
client = create_client_sync(
    url=st.secrets["TURSO_DATABASE_URL"],
    auth_token=st.secrets["TURSO_AUTH_TOKEN"]
)

st.title("Employee Score Portal")

uploaded_file = st.file_uploader(
    "Upload monthly_scores.csv",
    type=["csv"]
)

if uploaded_file:

    # Read CSV
    df = pd.read_csv(uploaded_file)

    # Remove completely empty columns
    df = df.dropna(axis=1, how="all")

    # Clean column names
    df.columns = df.columns.str.strip()

    st.
