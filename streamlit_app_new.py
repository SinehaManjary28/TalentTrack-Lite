import streamlit as st
import pandas as pd

from db import (
    init_db,
    insert_candidate,
    find_duplicate,
    update_candidate,
    get_all_candidates
)
from validators import validate_candidate

# --------------------------------------------------
# Page Configuration
# --------------------------------------------------
st.set_page_config(
    page_title="TalentTrack Lite",
    layout="wide"
)

st.title("TalentTrack Lite")
st.caption("Candidate Management System using Streamlit and SQLite")

# --------------------------------------------------
# Initialize Database
# --------------------------------------------------
init_db()

# --------------------------------------------------
# Sidebar Navigation
# --------------------------------------------------
st.sidebar.header("Navigation")
menu = st.sidebar.radio(
    "Select an option",
    ["Upload Candidates", "View Candidates"]
)

# --------------------------------------------------
# Helper Functions
# --------------------------------------------------
def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [col.strip().lower() for col in df.columns]
    df = df.where(pd.notnull(df), None)
    return df


def validate_dataframe(df: pd.DataFrame):
    errors = []

    for index, row in df.iterrows():
        candidate = {
            "candidate_name": row.get("candidate_name"),
            "skills": row.get("skills"),
            "phone": str(row.get("phone")) if row.get("phone") else None,
            "email": row.get("email"),
            "location": row.get("location"),
            "available_time": row.get("available_time"),
            "status": row.get("status"),
            "notes": row.get("notes")
        }

        is_valid, error = validate_candidate(candidate)
        if not is_valid:
            errors.append(f"Row {index + 2}: {error}")

    return errors


def save_to_db(df: pd.DataFrame):
    inserted, updated, skipped = 0, 0, 0

    for _, row in df.iterrows():
        candidate = {
            "candidate_name": row.get("candidate_name"),
            "skills": row.get("skills"),
            "phone": str(row.get("phone")) if row.get("phone") else None,
            "email": row.get("email"),
            "location": row.get("location"),
            "available_time": row.get("available_time"),
            "status": row.get("status"),
            "notes": row.get("notes")
        }

        is_valid, _ = validate_candidate(candidate)
        if not is_valid:
            skipped += 1
            continue

        existing = find_duplicate(candidate["email"], candidate["phone"])
        if existing:
            update_candidate(existing["candidate_id"], candidate)
            updated += 1
        else:
            if insert_candidate(candidate):
                inserted += 1
            else:
                skipped += 1

    return inserted, updated, skipped


# --------------------------------------------------
# Upload Candidates Page
# --------------------------------------------------
if menu == "Upload Candidates":
    st.header("Upload Candidate Excel File")
    st.write("Upload an Excel (.xlsx) file to validate and store candidate information.")

    uploaded_file = st.file_uploader(
        "Select Excel file",
        type=["xlsx"]
    )

    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        df = normalize_dataframe(df)

        st.success("File uploaded successfully")
        st.subheader("Data Preview")
        st.dataframe(df, use_container_width=True)

        col1, col2 = st.columns(2)

        with col1:
            validate_btn = st.button("Validate Data", use_container_width=True)

        with col2:
            save_btn = st.button("Save to Database", use_container_width=True)

        if validate_btn:
            with st.spinner("Validating data..."):
                errors = validate_dataframe(df)

            if errors:
                st.error("Validation Failed")
                for err in errors:
                    st.write(err)
            else:
                st.success("All records passed validation")

        if save_btn:
            with st.spinner("Saving records..."):
                inserted, updated, skipped = save_to_db(df)

            st.success("Database operation completed")

            c1, c2, c3 = st.columns(3)
            c1.metric("Inserted", inserted)
            c2.metric("Updated", updated)
            c3.metric("Skipped", skipped)


# --------------------------------------------------
# View Candidates Page
# --------------------------------------------------
elif menu == "View Candidates":
    st.header("Stored Candidates")
    st.write("List of all candidates currently stored in the database.")

    rows = get_all_candidates()

    if not rows:
        st.info("No candidate records found.")
    else:
        df = pd.DataFrame([dict(row) for row in rows])

        with st.expander("Filters"):
            status_filter = st.multiselect(
                "Filter by status",
                options=sorted(df["status"].dropna().unique().tolist())
            )

            if status_filter:
                df = df[df["status"].isin(status_filter)]

        st.dataframe(df, use_container_width=True)
        st.caption(f"Total candidates: {len(df)}")
