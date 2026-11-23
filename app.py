
import streamlit as st
from libsql_client import create_client_sync

@st.cache_resource
def connect_db():
    database_url = st.secrets["TURSO_DATABASE_URL"]
    auth_token = st.secrets["TURSO_AUTH_TOKEN"]

    # Use HTTPS instead of the WebSocket transport.
    if database_url.startswith("libsql://"):
        database_url = database_url.replace(
            "libsql://", "https://", 1
        )

    client = create_client_sync(
        url=database_url,
        auth_token=auth_token
    )

    # Actually test the database connection.
    result = client.execute("SELECT 1")

    if not result.rows or result.rows[0][0] != 1:
        raise RuntimeError("Turso connection test failed.")

    return client


try:
    client = connect_db()
    st.success("Turso database connection verified!")

except Exception as e:
    st.error(f"Turso connection failed: {e}")
    st.stop()

client.execute("""
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    month TEXT,
    month_key INTEGER,
    vertical TEXT,
    employee_id TEXT NOT NULL,
    power_unit TEXT,
    position TEXT,
    name TEXT NOT NULL,
    supervisor TEXT,
    qualified TEXT,
    final_score TEXT,
    accuracy TEXT
)
""")

st.success("Employee database table is ready!")
