
import streamlit as st
import pandas as pd
import hmac
import uuid

from libsql_client import create_client_sync


# =====================================================
# 1. APP CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="Employee Score Portal",
    page_icon="👤",
    layout="wide"
)

REQUIRED_COLUMNS = [
    "Month",
    "Vertical",
    "Employee ID",
    "Power Unit",
    "Position",
    "Name",
    "Supervisor",
    "Qualified?",
    "Final Score",
    "Accuracy"
]


# =====================================================
# 2. CONNECT TO TURSO
# =====================================================

@st.cache_resource
def connect_db():

    database_url = st.secrets["TURSO_DATABASE_URL"]
    auth_token = st.secrets["TURSO_AUTH_TOKEN"]

    # Use HTTPS transport, which is working in your app.
    if database_url.startswith("libsql://"):
        database_url = database_url.replace(
            "libsql://",
            "https://",
            1
        )

    db = create_client_sync(
        url=database_url,
        auth_token=auth_token
    )

    # Verify the connection with an actual query.
    result = db.execute("SELECT 1")

    if result.rows[0][0] != 1:
        raise RuntimeError("Database verification failed.")

    return db


try:
    client = connect_db()
except Exception as e:
    st.error(f"Turso connection failed: {e}")
    st.stop()


# =====================================================
# 3. DATABASE INITIALIZATION
# =====================================================

client.execute("""
CREATE TABLE IF NOT EXISTS portal_config (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")


def get_active_table():

    result = client.execute("""
        SELECT value
        FROM portal_config
        WHERE key = ?
    """, ["active_table"])

    if not result.rows:
        return None

    table_name = result.rows[0][0]

    # Only accept generated table identifiers.
    if (
        not table_name
        or not table_name.startswith("employee_data_")
        or not table_name.replace("_", "").isalnum()
    ):
        raise RuntimeError("Invalid active dataset configuration.")

    return table_name


# =====================================================
# 4. PREPARE CSV DATA
# =====================================================

def normalize_month(value):

    value = str(value).strip()

    if not value:
        raise ValueError("A record has a blank Month value.")

    parsed = pd.to_datetime(
        value,
        errors="coerce"
    )

    # Also support Excel date serial numbers.
    if pd.isna(parsed) and value.isdigit():

        parsed = pd.to_datetime(
            float(value),
            unit="D",
            origin="1899-12-30",
            errors="coerce"
        )

    if pd.isna(parsed):
        raise ValueError(
            f"Cannot interpret Month value: {value}"
        )

    return (
        parsed.strftime("%Y-%m"),
        int(parsed.strftime("%Y%m"))
    )


def prepare_csv(uploaded_file):

    df = pd.read_csv(
        uploaded_file,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig"
    )

    df.columns = df.columns.str.strip()

    missing = [
        col for col in REQUIRED_COLUMNS
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            "Missing CSV columns: " + ", ".join(missing)
        )

    df = df[REQUIRED_COLUMNS].copy()

    # Clean text values.
    for col in REQUIRED_COLUMNS:
        df[col] = df[col].astype(str).str.strip()

    # Remove completely empty rows.
    df = df[
        df.apply(
            lambda row: any(value != "" for value in row),
            axis=1
        )
    ].copy()

    # Employee ID and Name are mandatory.
    df = df[
        (df["Employee ID"] != "") &
        (df["Name"] != "")
    ].copy()

    if df.empty:
        raise ValueError("No valid employee records found.")

    # Normalize reporting months.
    normalized = df["Month"].apply(normalize_month)

    df["month"] = normalized.apply(lambda x: x[0])
    df["month_key"] = normalized.apply(lambda x: x[1])

    return df


# =====================================================
# 5. SAFE DATASET IMPORT
# =====================================================

def import_dataset(df):

    # Every upload gets a new unpublished table.
    table_name = "employee_data_" + uuid.uuid4().hex

    client.execute(f"""
        CREATE TABLE {table_name} (
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

    insert_sql = f"""
        INSERT INTO {table_name} (
            month,
            month_key,
            vertical,
            employee_id,
            power_unit,
            position,
            name,
            supervisor,
            qualified,
            final_score,
            accuracy
        )
        VALUES
    """

    records = []

    for _, row in df.iterrows():

        records.append((
            row["month"],
            int(row["month_key"]),
            row["Vertical"],
            row["Employee ID"],
            row["Power Unit"],
            row["Position"],
            row["Name"],
            row["Supervisor"],
            row["Qualified?"],
            row["Final Score"],
            row["Accuracy"]
        ))

    # Insert in batches.
    # Each batch contains 50 rows x 11 columns.
    batch_size = 50

    for start in range(0, len(records), batch_size):

        batch = records[start:start + batch_size]

        placeholders = ", ".join(
            ["(" + ",".join(["?"] * 11) + ")"]
            * len(batch)
        )

        sql = insert_sql + placeholders

        parameters = [
            value
            for record in batch
            for value in record
        ]

        client.execute(sql, parameters)

    # Verify that every row was inserted.
    count_result = client.execute(
        f"SELECT COUNT(*) FROM {table_name}"
    )

    imported_count = count_result.rows[0][0]

    if imported_count != len(records):
        raise RuntimeError(
            f"Import verification failed. "
            f"Expected {len(records)}, found {imported_count}."
        )

    # Publish the new dataset only after verification.
    # This single statement changes which table is active.
    client.execute("""
        INSERT INTO portal_config (key, value)
        VALUES (?, ?)
        ON CONFLICT(key)
        DO UPDATE SET value = excluded.value
    """, ["active_table", table_name])

    return table_name, imported_count


# =====================================================
# 6. ADMIN AUTHENTICATION
# =====================================================

def admin_login():

    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False

    if st.session_state.admin_authenticated:
        return True

    st.subheader("Administrator Login")

    password = st.text_input(
        "Administrator Password",
        type="password"
    )

    if st.button("Log in"):

        expected = st.secrets["ADMIN_PASSWORD"]

        if hmac.compare_digest(password, expected):

            st.session_state.admin_authenticated = True
            st.rerun()

        else:
            st.error("Incorrect password.")

    return False


# =====================================================
# 7. ADMIN UPLOAD PAGE
# =====================================================

def upload_page():

    st.title("Employee Data Administration")

    if not admin_login():
        return

    if st.button("Log out"):
        st.session_state.admin_authenticated = False
        st.rerun()

    st.divider()

    st.subheader("Upload Monthly Employee CSV")

    st.warning(
        "The new upload will replace the active dataset "
        "only after successful import and verification."
    )

    uploaded_file = st.file_uploader(
        "Select monthly_scores.csv",
        type=["csv"]
    )

    if uploaded_file is None:
        return

    try:

        df = prepare_csv(uploaded_file)

        st.success("CSV validation successful.")

        st.write(
            f"Records ready for import: **{len(df):,}**"
        )

        st.dataframe(
            df[REQUIRED_COLUMNS].head(20),
            use_container_width=True
        )

        if st.button("Confirm and Import", type="primary"):

            with st.spinner("Importing records into Turso..."):

                table_name, count = import_dataset(df)

            st.success(
                f"Successfully imported {count:,} employee records!"
            )

            st.info(
                "The new dataset is now active. "
                "Your previous dataset has been retained."
            )

    except Exception as e:

        st.error(f"Import failed: {e}")

        st.warning(
            "The previous active dataset has not been replaced. "
            "You can correct the CSV and try again."
        )


# =====================================================
# 8. PUBLIC EMPLOYEE SEARCH
# =====================================================

def search_page():

    st.title("Employee Search Portal")

    st.caption(
        "Search employees by Employee ID or Name."
    )

    table_name = get_active_table()

    if not table_name:

        st.info(
            "No employee data has been uploaded yet."
        )
        return

    search = st.text_input(
        "Employee ID or Name",
        placeholder="Enter Employee ID or Name"
    )

    if not search.strip():
        return

    result = client.execute(
        f"""
        SELECT
            e.employee_id,
            e.name
        FROM {table_name} e
        WHERE e.id = (
            SELECT x.id
            FROM {table_name} x
            WHERE x.employee_id = e.employee_id
            ORDER BY x.month_key DESC, x.id DESC
            LIMIT 1
        )
        AND (
            instr(lower(e.employee_id), lower(?)) > 0
            OR instr(lower(e.name), lower(?)) > 0
        )
        ORDER BY e.name
        LIMIT 100
        """,
        [search.strip(), search.strip()]
    )

    if not result.rows:

        st.warning("No matching employees found.")
        return

    choices = {
        f"{row[1]} ({row[0]})": row[0]
        for row in result.rows
    }

    selected = st.selectbox(
        "Select Employee",
        list(choices.keys())
    )

    employee_id = choices[selected]

    profile = client.execute(
        f"""
        SELECT
            month,
            vertical,
            employee_id,
            power_unit,
            position,
            name,
            supervisor,
            qualified,
            final_score,
            accuracy
        FROM {table_name}
        WHERE employee_id = ?
        ORDER BY month_key DESC, id DESC
        LIMIT 1
        """,
        [employee_id]
    )

    if not profile.rows:
        st.warning("Employee profile not found.")
        return

    row = profile.rows[0]

    st.divider()

    st.subheader(row[5])

    st.caption(f"Employee ID: {row[2]}")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Latest Month",
        row[0] or "—"
    )

    col2.metric(
        "Final Score",
        row[8] or "—"
    )

    col3.metric(
        "Accuracy",
        row[9] or "—"
    )

    st.subheader("Employee Details")

    st.write("**Vertical:**", row[1] or "—")
    st.write("**Power Unit:**", row[3] or "—")
    st.write("**Position:**", row[4] or "—")
    st.write("**Supervisor:**", row[6] or "—")
    st.write("**Qualified?:**", row[7] or "—")


# =====================================================
# 9. MAIN APP
# =====================================================

st.sidebar.success("Database connected")

page = st.sidebar.radio(
    "Navigation",
    ["Employee Search", "Administrator"]
)

if page == "Employee Search":
    search_page()

else:
    upload_page()
