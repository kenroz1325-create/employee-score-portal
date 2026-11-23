import streamlit as st
import pandas as pd
from libsql_client import create_client_sync

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

    df = pd.read_csv(uploaded_file)

    st.success(f"Loaded {len(df)} rows")

    if st.button("Upload to Turso"):

        uploaded = 0

        for _, row in df.iterrows():

            client.execute("""
                INSERT INTO monthly_scores (
                    month,
                    vertical,
                    employee_id,
                    power_unit,
                    position,
                    name,
                    supervisor,
                    qualified,
                    final_score,
                    accuracy,
                    ranking,
                    validation,
                    quarter
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                str(row["Month"]),
                str(row["Vertical"]),
                str(row["Employee ID"]),
                str(row["Power Unit"]),
                str(row["Position"]),
                str(row["Name"]),
                str(row["Supervisor"]),
                str(row["Qualified? "]),
                str(row["Final Score"]),
                str(row["Accuracy"]),
                str(row["Ranking"]),
                str(row["Validation"]),
                str(row["Quarter"])
            ])

            uploaded += 1

        st.success(f"Uploaded {uploaded} rows to Turso!")
