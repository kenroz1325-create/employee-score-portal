
import streamlit as st
import pandas as pd
from libsql_client import create_client_sync

st.set_page_config(
    page_title="Employee Score Portal",
    page_icon="👤",
    layout="wide"
)

# --------------------------------------------------
# TURSO CONNECTION
# --------------------------------------------------

@st.cache_resource
def connect_db():
    return create_client_sync(
        url=st.secrets["TURSO_DATABASE_URL"],
        auth_token=st.secrets["TURSO_AUTH_TOKEN"]
    )

try:
    client = connect_db()
    st.sidebar.success("Database connected")

except Exception as e:
    st.error(f"Database connection failed: {e}")
    st.stop()


# --------------------------------------------------
# CREATE TABLE
# --------------------------------------------------

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

client.execute("""
CREATE INDEX IF NOT EXISTS idx_employee_id
ON employees(employee_id)
""")

client.execute("""
CREATE INDEX IF NOT EXISTS idx_employee_name
ON employees(name)
""")


# --------------------------------------------------
# PAGE NAVIGATION
# --------------------------------------------------

page = st.sidebar.radio(
    "Navigation",
    ["Employee Search", "Upload Data"]
)


# --------------------------------------------------
# UPLOAD DATA
# --------------------------------------------------

if page == "Upload Data":

    st.title("Upload Employee Data")

    uploaded_file = st.file_uploader(
        "Upload your monthly employee CSV",
        type=["csv"]
    )

    if uploaded_file:

        try:
            df = pd.read_csv(
                uploaded_file,
                dtype=str
            ).fillna("")

            df.columns = df.columns.str.strip()

            required_columns = [
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

            missing = [
                col for col in required_columns
                if col not in df.columns
            ]

            if missing:
                st.error(
                    "Missing columns: " + ", ".join(missing)
                )

            else:

                df = df[required_columns].copy()

                df = df[
                    (df["Employee ID"].str.strip() != "") &
                    (df["Name"].str.strip() != "")
                ].copy()

                st.subheader("Preview")
                st.dataframe(
                    df.head(20),
                    use_container_width=True
                )

                st.write(
                    f"Records ready to import: {len(df):,}"
                )

                if st.button("Import into Turso"):

                    try:
                        # Prepare normalized rows
                        records = []

                        for _, row in df.iterrows():

                            month_value = row["Month"].strip()
                            parsed_month = pd.to_datetime(
                                month_value,
                                errors="coerce"
                            )

                            if pd.isna(parsed_month):
                                month_text = month_value
                                month_key = 0
                            else:
                                month_text = parsed_month.strftime(
                                    "%Y-%m"
                                )
                                month_key = int(
                                    parsed_month.strftime("%Y%m")
                                )

                            records.append((
                                month_text,
                                month_key,
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

                        # Replace previous dataset
                        client.execute("DELETE FROM employees")

                        insert_sql = """
                        INSERT INTO employees (
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
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """

                        # Import in batches
                        batch_size = 100

                        for start in range(
                            0,
                            len(records),
                            batch_size
                        ):
                            batch = records[
                                start:start + batch_size
                            ]

                            for record in batch:
                                client.execute(
                                    insert_sql,
                                    list(record)
                                )

                        st.success(
                            f"Successfully imported {len(records):,} records!"
                        )

                    except Exception as e:
                        st.error(f"Import failed: {e}")

        except Exception as e:
            st.error(f"CSV reading error: {e}")


# --------------------------------------------------
# EMPLOYEE SEARCH
# --------------------------------------------------

elif page == "Employee Search":

    st.title("Employee Search Portal")

    search = st.text_input(
        "Search Employee ID or Name",
        placeholder="Enter Employee ID or Name"
    )

    if search.strip():

        try:

            result = client.execute(
                """
                SELECT
                    employee_id,
                    name,
                    MAX(month_key)
                FROM employees
                WHERE employee_id LIKE ?
                   OR name LIKE ?
                GROUP BY employee_id, name
                ORDER BY name
                LIMIT 100
                """,
                [
                    f"%{search}%",
                    f"%{search}%"
                ]
            )

            employees = result.rows

            if not employees:

                st.warning("No employee found.")

            else:

                choices = {
                    f"{row[1]} ({row[0]})": row[0]
                    for row in employees
                }

                selected = st.selectbox(
                    "Select Employee",
                    list(choices.keys())
                )

                employee_id = choices[selected]

                profile = client.execute(
                    """
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
                    FROM employees
                    WHERE employee_id = ?
                    ORDER BY month_key DESC, id DESC
                    LIMIT 1
                    """,
                    [employee_id]
                )

                if profile.rows:

                    row = profile.rows[0]

                    st.divider()
                    st.subheader(row[5])

                    st.caption(
                        f"Employee ID: {row[2]}"
                    )

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

                    st.write("**Vertical:**", row[1])
                    st.write("**Power Unit:**", row[3])
                    st.write("**Position:**", row[4])
                    st.write("**Supervisor:**", row[6])
                    st.write("**Qualified?:**", row[7])

        except Exception as e:
            st.error(f"Search error: {e}")
