import streamlit as st
import pandas as pd
import re

from db import (
    get_all_candidates,
    insert_candidate,
    update_candidate,
    find_duplicate
)

# ---------------- CONFIG ----------------
st.set_page_config(page_title="TalentTrack Lite", layout="wide")

STATUS_OPTIONS = ["Applied", "Interview", "Selected", "Rejected"]

REQUIRED_COLUMNS = [
    "name",
    "skill",
    "phone",
    "email",
    "location",
    "available_time",
    "status",
    "notes"
]

# ---------------- HELPERS ----------------
def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def is_valid_phone(phone):
    return phone.isdigit() and len(phone) == 10

def load_data():
    data = get_all_candidates()
    return pd.DataFrame(data)

# ---------------- SIDEBAR ----------------
st.sidebar.title("TalentTrack Lite")
page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Add Candidate",
        "View / Search",
        "Update Candidate",
        "Import from Excel",
        "Export to Excel",
    ]
)

# ---------------- DASHBOARD ----------------
if page == "Dashboard":
    st.title("Dashboard")

    df = load_data()

    if df.empty:
        st.info("No candidates found.")
    else:
        total = len(df)
        st.metric("Total Candidates", total)

        st.subheader("Status Breakdown")
        status_counts = df["status"].value_counts()

        cols = st.columns(len(status_counts))
        for col, (status, count) in zip(cols, status_counts.items()):
            col.metric(status, count)

# ---------------- ADD CANDIDATE ----------------
elif page == "Add Candidate":
    st.title("Add Candidate")

    with st.form("add_form"):
        name = st.text_input("Name *")
        skill = st.text_input("Skill *")
        phone = st.text_input("Phone *")
        email = st.text_input("Email *")
        location = st.text_input("Location *")
        available_time = st.text_input("Available Time")
        status = st.selectbox("Status", STATUS_OPTIONS)
        notes = st.text_area("Notes")

        submitted = st.form_submit_button("Add Candidate")

    if submitted:
        if not all([name, skill, phone, email, location]):
            st.error("Please fill all required fields.")
        elif not is_valid_email(email):
            st.error("Invalid email format.")
        elif not is_valid_phone(phone):
            st.error("Phone must be 10 digits.")
        else:
            duplicate = find_duplicate(email, phone)

            if duplicate:
                st.warning("Duplicate candidate found.")
                st.json(duplicate)
            else:
                insert_candidate({
                    "name": name,
                    "skill": skill,
                    "phone": phone,
                    "email": email,
                    "location": location,
                    "available_time": available_time,
                    "status": status,
                    "notes": notes,
                })
                st.success("Candidate added successfully.")

# ---------------- VIEW / SEARCH ----------------
elif page == "View / Search":
    st.title("View / Search Candidates")

    df = load_data()

    if df.empty:
        st.info("No data available.")
    else:
        col1, col2, col3, col4 = st.columns(4)

        name_f = col1.text_input("Filter by Name")
        skill_f = col2.text_input("Filter by Skill")
        location_f = col3.text_input("Filter by Location")
        status_f = col4.selectbox("Status", ["All"] + STATUS_OPTIONS)

        if name_f:
            df = df[df["name"].str.contains(name_f, case=False)]
        if skill_f:
            df = df[df["skill"].str.contains(skill_f, case=False)]
        if location_f:
            df = df[df["location"].str.contains(location_f, case=False)]
        if status_f != "All":
            df = df[df["status"] == status_f]

        st.dataframe(df, use_container_width=True)

# ---------------- UPDATE ----------------
elif page == "Update Candidate":
    st.title("Update Candidate")

    df = load_data()

    if df.empty:
        st.info("No candidates available.")
    else:
        selected = st.selectbox(
            "Select Candidate",
            df["email"]
        )

        row = df[df["email"] == selected].iloc[0]

        with st.form("update_form"):
            name = st.text_input("Name", row["name"])
            skill = st.text_input("Skill", row["skill"])
            phone = st.text_input("Phone", row["phone"])
            location = st.text_input("Location", row["location"])
            available_time = st.text_input("Available Time", row["available_time"])
            status = st.selectbox("Status", STATUS_OPTIONS, index=STATUS_OPTIONS.index(row["status"]))
            notes = st.text_area("Notes", row["notes"])

            updated = st.form_submit_button("Update")

        if updated:
            update_candidate(row["id"], {
                "name": name,
                "skill": skill,
                "phone": phone,
                "location": location,
                "available_time": available_time,
                "status": status,
                "notes": notes,
            })
            st.success("Candidate updated successfully.")

# ---------------- IMPORT ----------------
elif page == "Import from Excel":
    st.title("Import from Excel")

    file = st.file_uploader("Upload Excel File", type=["xlsx"])

    if file:
        df = pd.read_excel(file)
        st.subheader("Preview")
        st.dataframe(df.head())

        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]

        if missing:
            st.error(f"Missing columns: {missing}")
        else:
            if st.button("Import Data"):
                inserted = skipped = 0

                for _, row in df.iterrows():
                    dup = find_duplicate(row["email"], str(row["phone"]))

                    if dup:
                        skipped += 1
                        continue

                    insert_candidate(row.to_dict())
                    inserted += 1

                st.success(f"Import complete. Inserted: {inserted}, Skipped: {skipped}")

# ---------------- EXPORT ----------------
elif page == "Export to Excel":
    st.title("Export Data")

    df = load_data()

    if df.empty:
        st.info("No data to export.")
    else:
        st.download_button(
            "Download Excel",
            df.to_excel(index=False),
            file_name="candidates.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
