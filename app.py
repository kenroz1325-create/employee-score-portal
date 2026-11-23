
import streamlit as st
import pandas as pd
from libsql_client import create_client_sync

# Page configuration
st.set_page_config(
    page_title="Employee Score Portal",
    page_icon="👤",
    layout="wide"
)

# Connect to Turso
try:
    client = create_client_sync(
        url=st.secrets["TURSO_DATABASE_URL"],
        auth_token=st.secrets["TURSO_AUTH_TOKEN"]
    )
    st.success("Connected to Turso successfully!")

except Exception as e:
    st.error(f"Turso connection failed: {e}")
    st.stop()

# App title
st.title("Employee Score Portal")

st.write("Upload your monthly employee scores CSV file.")

# CSV upload
uploaded_file = st.file_uploader(
    "Upload monthly_scores.csv",
    type=["csv"]
)

if uploaded_file:

    try:
        # Read CSV
        df = pd.read_csv(uploaded_file)

        # Remove completely empty columns
        df = df.dropna(axis=1, how="all")

        # Clean column names
        df.columns = df.columns.str.strip()

        st.success("CSV uploaded successfully!")

        # Preview data
        st.subheader("Data Preview")
        st.dataframe(df.head(20), use_container_width=True)

        st.write(f"Total records: {len(df):,}")

    except Exception as e:
        st.error(f"CSV processing error: {e}")
