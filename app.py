import streamlit as st
import pandas as pd

st.title("CSV Upload Test")

uploaded_file = st.file_uploader(
    "Upload monthly_scores.csv",
    type=["csv"]
)

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    st.success(f"Loaded {len(df)} rows")
    st.dataframe(df.head())
