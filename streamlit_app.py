import streamlit as st
import pandas as pd

from db import (
    init_db,
    insert_candidate,
    find_duplicate,
    update_candidate,
    delete_candidate,
    get_all_candidates
)

from validators import validate_candidate
from import_export import (
    preview_excel,
    import_candidates_from_excel,
    export_candidates_to_excel
)


# -----------------------------
# Helper functions
# -----------------------------
def clean_candidate_form(values):
    """
    Trim and clean the values.
    """
    return {
        "candidate_name": str(values.get("candidate_name", "")).strip(),
        "skills": str(values.get("skills", "")).strip() or None,
        "phone": str(values.get("phone", "")).strip(),
        "email": str(values.get("email", "")).strip().lower(),
        "location": str(values.get("location", "")).strip() or None,
        "available_time": str(values.get("available_time", "")).strip() or None,
        "status": str(values.get("status", "")).strip(),
        "notes": str(values.get("notes", "")).strip() or None
    }


def show_success(message):
    st.success(message)


def show_error(message):
    st.error(message)


def show_warning(message):
    st.warning(message)


# -----------------------------
# Pages
# -----------------------------
def dashboard_page():
    st.title("Dashboard")

    rows = get_all_candidates()
    df = pd.DataFrame([dict(row) for row in rows])

    total = len(df)
    st.metric("Total Candidates", total)

    if total > 0:
        st.write(df.groupby("status").size().reset_index(name="count"))
    else:
        st.info("No candidates yet.")


def add_candidate_page():
    st.title(" Add Candidate")

    with st.form("add_candidate_form"):
        name = st.text_input("Candidate Name")
        skills = st.text_input("Skills")
        phone = st.text_input("Phone")
        email = st.text_input("Email")
        location = st.text_input("Location")
        available_time = st.text_input("Available Time")
        status = st.selectbox("Status", ["New", "In Progress", "Selected", "Rejected"])
        notes = st.text_area("Notes")

        submitted = st.form_submit_button("Save")

        if submitted:
            candidate = clean_candidate_form({
                "candidate_name": name,
                "skills": skills,
                "phone": phone,
                "email": email,
                "location": location,
                "available_time": available_time,
                "status": status,
                "notes": notes
            })

            # Validate
            is_valid, error = validate_candidate(candidate)
            if not is_valid:
                show_error(error)
                return

            # Duplicate check
            existing = find_duplicate(candidate["email"], candidate["phone"])
            if existing:
                show_warning("Duplicate found! Email or Phone already exists.")
                st.write(dict(existing))
                if st.button("Update Existing"):
                    update_candidate(existing["candidate_id"], candidate)
                    show_success("Updated successfully!")
                return

            # Insert
            success = insert_candidate(candidate)
            if success:
                show_success("Candidate added successfully!")
            else:
                show_error("Candidate already exists (email/phone duplicate).")


def view_search_page():
    st.title("🔎 View / Search Candidates")

    rows = get_all_candidates()
    df = pd.DataFrame([dict(row) for row in rows])

    if df.empty:
        st.info("No candidates to show.")
        return

    name_filter = st.text_input("Search by Name")
    skill_filter = st.text_input("Search by Skills")
    location_filter = st.text_input("Search by Location")
    status_filter = st.selectbox("Status", ["All", "New", "In Progress", "Selected", "Rejected"])

    if name_filter:
        df = df[df["candidate_name"].str.contains(name_filter, case=False)]
    if skill_filter:
        df = df[df["skills"].str.contains(skill_filter, case=False)]
    if location_filter:
        df = df[df["location"].str.contains(location_filter, case=False)]
    if status_filter != "All":
        df = df[df["status"] == status_filter]

    st.dataframe(df)


def update_candidate_page():
    st.title("Update Candidate")

    rows = get_all_candidates()
    df = pd.DataFrame([dict(row) for row in rows])

    if df.empty:
        st.info("No candidates to update.")
        return

    candidate_id = st.selectbox("Select Candidate", df["candidate_id"].tolist())
    candidate = df[df["candidate_id"] == candidate_id].iloc[0]

    with st.form("update_form"):
        name = st.text_input("Candidate Name", candidate["candidate_name"])
        skills = st.text_input("Skills", candidate["skills"] or "")
        phone = st.text_input("Phone", candidate["phone"])
        email = st.text_input("Email", candidate["email"])
        location = st.text_input("Location", candidate["location"] or "")
        available_time = st.text_input("Available Time", candidate["available_time"] or "")
        status = st.selectbox("Status", ["New", "In Progress", "Selected", "Rejected"], index=["New", "In Progress", "Selected", "Rejected"].index(candidate["status"]))
        notes = st.text_area("Notes", candidate["notes"] or "")

        submitted = st.form_submit_button("Update")

        if submitted:
            updated = clean_candidate_form({
                "candidate_name": name,
                "skills": skills,
                "phone": phone,
                "email": email,
                "location": location,
                "available_time": available_time,
                "status": status,
                "notes": notes
            })

            is_valid, error = validate_candidate(updated)
            if not is_valid:
                show_error(error)
                return

            update_candidate(candidate_id, updated)
            show_success("Candidate updated successfully!")


def delete_candidate_page():
    st.title("Delete Candidate")

    rows = get_all_candidates()
    df = pd.DataFrame([dict(row) for row in rows])

    if df.empty:
        st.info("No candidates to delete.")
        return

    candidate_id = st.selectbox("Select Candidate", df["candidate_id"].tolist())
    candidate = df[df["candidate_id"] == candidate_id].iloc[0]

    st.write(candidate)

    if st.button("Delete"):
        delete_candidate(candidate_id)
        show_success("Candidate deleted successfully!")


def import_excel_page():
    st.title("Import from Excel")

    uploaded_file = st.file_uploader("Upload Excel file (.xlsx)", type=["xlsx"])
    if uploaded_file:
        st.info("Previewing Excel file...")

        # Preview
        preview = preview_excel(uploaded_file)
        st.table(preview)

        if st.button("Import Now"):
            result = import_candidates_from_excel(uploaded_file)
            show_success(
                f"Import complete! Inserted: {result['inserted']} | Updated: {result['updated']} | Skipped: {result['skipped']}"
            )


def export_excel_page():
    st.title("Export to Excel")

    if st.button("Export Now"):
        output_file = export_candidates_to_excel()
        st.success(f"Exported successfully to {output_file}")


# -----------------------------
# Main
# -----------------------------
def main():
    init_db()

    st.sidebar.title("TalentTrack")
    page = st.sidebar.selectbox(
        "Navigation",
        [
            "Dashboard",
            "Add Candidate",
            "View/Search Candidates",
            "Update Candidate",
            "Delete Candidate",
            "Import from Excel",
            "Export to Excel"
        ]
    )

    if page == "Dashboard":
        dashboard_page()
    elif page == "Add Candidate":
        add_candidate_page()
    elif page == "View/Search Candidates":
        view_search_page()
    elif page == "Update Candidate":
        update_candidate_page()
    elif page == "Delete Candidate":
        delete_candidate_page()
    elif page == "Import from Excel":
        import_excel_page()
    elif page == "Export to Excel":
        export_excel_page()


if __name__ == "__main__":
    main()
