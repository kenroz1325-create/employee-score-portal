import streamlit as st
import pandas as pd
from libsql_client import create_client_sync

st.set_page_config(page_title="Employee Score Portal")

# Connect to Turso
client = create_client_sync(
    url=st.secrets["libsql://employee-portal-kennethrozon.aws-ap-southeast-1.turso.io"],
    auth_token=st.secrets["eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3OTU0MzQzNTMsImlkIjoiMDFhMjA4MzEtOWYwMS03Njg0LWIzOWQtODA2NTBmN2M4OGIwIiwia2lkIjoiak9qbGgyZWU5ZEJ0d1dkSVRBOG9fZzF3VmhKazJnaTY4cHNnSTJLbXFaUSIsInJpZCI6IjA3YmFiMDFjLTQwOTAtNDlkNS1hOWJjLTM1MTA0MGE4MWI5OSJ9.2OJdyMIhKMCSWWWTJNgzdMUiwWdTKDeO04atMQR3TbKG5a3EA_swQSvsgK8lVajID3wK0_OyFE2mCxMBQLZTBA"]
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
