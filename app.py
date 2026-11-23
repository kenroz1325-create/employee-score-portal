import streamlit as st
import pandas as pd
from libsql_client import create_client_sync

st.set_page_config(page_title="Employee Score Portal")

# Connect to Turso
client = create_client_sync(
    url=st.secrets["TURSO_DATABASE_URL"],
    auth_token=st.secrets["TURSO_AUTH_TOKEN"]
)

st.title("Employee Score Portal")

search = st.text_input(
    "Search Employee Name or Employee ID"
)

if search:

    query = """
    SELECT *
    FROM monthly_scores
    WHERE
        LOWER(name) LIKE LOWER(?)
        OR employee_id LIKE ?
    LIMIT 100
    """

    result = client.execute(
        query,
        [f"%{search}%", f"%{search}%"]
    )

    rows = result.rows

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("No records found.")
