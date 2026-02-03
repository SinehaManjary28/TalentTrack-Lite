
# talenttrack_app.py - Complete TalentTrack Application with CSV Support
import os
import streamlit as st
import pandas as pd
import sqlite3
import uuid
import re
from typing import Tuple, Optional, Dict
from datetime import datetime, timedelta
from io import StringIO

# ============================================================================
# VALIDATION FUNCTIONS (Embedded from your code)
# ============================================================================

# Allowed status values (keep in sync with UI dropdown)
ALLOWED_STATUS = {"New", "In Progress", "Selected", "Rejected"}

# Country-wise phone rules (code : required digits)
COUNTRY_PHONE_RULES = {
    "+91": 10,
    "+1": 10,
    "+44": 10,
    "+61": 9,
    "+81": 10,
    "+49": 11,
    "+971": 9,
    "+65": 8
}


def validate_required_fields(candidate: Dict) -> Tuple[bool, Optional[str]]:
    required_fields = ["candidate_name", "email", "phone", "status", "country_code"]

    for field in required_fields:
        if field not in candidate or not str(candidate[field]).strip():
            return False, f"{field.replace('_', ' ').title()} is required."

    return True, None


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    email = email.strip().lower()
    email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"

    if not re.match(email_regex, email):
        return False, "Invalid email format."

    return True, None


def validate_phone(phone: str, country_code: str) -> Tuple[bool, Optional[str], Optional[str]]:
    if not phone:
        return False, "Phone number is required.", None

    phone = phone.strip()

    if not phone.isdigit():
        return False, "Phone number must contain only digits.", None

    if country_code not in COUNTRY_PHONE_RULES:
        return False, "Unsupported country code.", None

    required_length = COUNTRY_PHONE_RULES[country_code]

    if len(phone) != required_length:
        return False, f"Phone number must be {required_length} digits.", None

    normalized_phone = country_code + phone
    return True, None, normalized_phone


def validate_status(status: str) -> Tuple[bool, Optional[str]]:
    if status not in ALLOWED_STATUS:
        return False, f"Status must be one of {', '.join(ALLOWED_STATUS)}."

    return True, None


# 🔴 NEW: Name existence warning logic
def name_exists_warning(existing_name_record) -> Optional[str]:
    """
    Returns warning message if candidate name already exists.
    This is NOT a blocking validation.
    """
    if existing_name_record:
        return "Candidate with this name already exists."
    return None


def validate_candidate(candidate: Dict) -> Tuple[bool, Optional[str]]:
    # Required fields
    is_valid, error = validate_required_fields(candidate)
    if not is_valid:
        return False, error

    # Email
    is_valid, error = validate_email(candidate["email"])
    if not is_valid:
        return False, error

    # Phone
    is_valid, error, normalized_phone = validate_phone(
        candidate["phone"],
        candidate["country_code"]
    )
    if not is_valid:
        return False, error

    candidate["phone"] = normalized_phone

    # Status
    is_valid, error = validate_status(candidate["status"])
    if not is_valid:
        return False, error

    return True, None


def check_duplicate_logic(existing_record) -> Tuple[bool, Optional[str]]:
    if existing_record:
        return True, "Duplicate candidate found (email or phone already exists)."
    return False, None

# ============================================================================
# DATABASE FUNCTIONS (Embedded from your code)
# ============================================================================

# Fixed database path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "talenttrack.db")

# Threshold for re-adding candidate (3 months)
THRESHOLD_DAYS = 90


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            candidate_id TEXT PRIMARY KEY,
            candidate_name TEXT NOT NULL,
            skills TEXT,
            phone TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            location TEXT,
            available_time TEXT,
            status TEXT,
            notes TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)

    conn.commit()
    conn.close()


# --------------------------------------------------
# Threshold-based check
# --------------------------------------------------
def can_readd_candidate(email, phone):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT candidate_id, created_at
        FROM candidates
        WHERE email = ? OR phone = ?
        ORDER BY created_at DESC
        LIMIT 1
    """, (email, phone))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return True, None  # No previous record

    last_created = datetime.strptime(
        row["created_at"], "%Y-%m-%d %H:%M:%S"
    )

    if (datetime.now() - last_created).days >= THRESHOLD_DAYS:
        return True, row["candidate_id"]

    return False, None


def insert_candidate(data):
    # Check existing candidate
    can_readd, candidate_id = can_readd_candidate(
        data["email"], data["phone"]
    )

    if not can_readd:
        return False

    # If candidate exists and threshold passed → UPDATE
    if candidate_id:
        update_candidate(candidate_id, data)
        return True

    # Otherwise → INSERT new
    conn = get_connection()
    cursor = conn.cursor()

    candidate_id = str(uuid.uuid4())
    timestamp = get_timestamp()

    try:
        cursor.execute("""
            INSERT INTO candidates (
                candidate_id,
                candidate_name,
                skills,
                phone,
                email,
                location,
                available_time,
                status,
                notes,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            candidate_id,
            data["candidate_name"],
            data.get("skills"),
            data["phone"],
            data["email"],
            data.get("location"),
            data.get("available_time"),
            data.get("status"),
            data.get("notes"),
            timestamp,
            timestamp
        ))

        conn.commit()
        return True

    except sqlite3.IntegrityError:
        return False

    finally:
        conn.close()


def get_all_candidates():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM candidates")
    rows = cursor.fetchall()

    conn.close()
    return rows


def find_duplicate(email, phone):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM candidates
        WHERE email = ? OR phone = ?
    """, (email, phone))

    row = cursor.fetchone()
    conn.close()
    return row


def find_by_name(name):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM candidates
        WHERE candidate_name = ?
    """, (name,))

    row = cursor.fetchone()
    conn.close()
    return row


def update_candidate(candidate_id, updated_data):
    conn = get_connection()
    cursor = conn.cursor()

    timestamp = get_timestamp()

    cursor.execute("""
        UPDATE candidates
        SET
            candidate_name = ?,
            skills = ?,
            phone = ?,
            email = ?,
            location = ?,
            available_time = ?,
            status = ?,
            notes = ?,
            updated_at = ?
        WHERE candidate_id = ?
    """, (
        updated_data["candidate_name"],
        updated_data.get("skills"),
        updated_data["phone"],
        updated_data["email"],
        updated_data.get("location"),
        updated_data.get("available_time"),
        updated_data.get("status"),
        updated_data.get("notes"),
        timestamp,
        candidate_id
    ))

    conn.commit()
    conn.close()


def delete_candidate(candidate_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM candidates WHERE candidate_id = ?",
        (candidate_id,)
    )

    conn.commit()
    conn.close()

# ============================================================================
# IMPORT/EXPORT FUNCTIONS
# ============================================================================
class ImportExport:
    @staticmethod
    def normalize_dataframe(df):
        df.columns = [str(col).strip().lower().replace(" ", "_") for col in df.columns]
        df = df.where(pd.notnull(df), None)
        return df
    
    @staticmethod
    def read_file(file, file_type):
        try:
            if file_type == 'excel':
                if hasattr(file, 'read'):
                    return pd.read_excel(file)
                else:
                    return pd.read_excel(file)
            elif file_type == 'csv':
                if hasattr(file, 'read'):
                    file.seek(0)
                    return pd.read_csv(file, encoding='utf-8')
                else:
                    return pd.read_csv(file, encoding='utf-8')
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
        except Exception as e:
            raise Exception(f"Error reading {file_type.upper()} file: {str(e)}")
    
    @staticmethod
    def preview_file(file, file_type):
        try:
            df = ImportExport.read_file(file, file_type)
            df = ImportExport.normalize_dataframe(df)
            
            preview_results = []
            
            for index, row in df.iterrows():
                candidate = {
                    k: (str(v).strip() if v is not None else None)
                    for k, v in row.to_dict().items()
                }
                
                # Add default country_code if not present
                if "country_code" not in candidate:
                    candidate["country_code"] = "+91"  # Default
                
                is_valid, error = validate_candidate(candidate)
                
                preview_results.append({
                    "row_number": index + 2,
                    "status": "✅ Valid" if is_valid else "❌ Invalid",
                    "error": error if error else "No errors"
                })
            
            return preview_results
        except Exception as e:
            raise Exception(f"Preview failed: {str(e)}")
    
    @staticmethod
    def import_candidates_from_file(file, file_type):
        try:
            df = ImportExport.read_file(file, file_type)
            df = ImportExport.normalize_dataframe(df)
            
            inserted = 0
            updated = 0
            skipped = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    candidate = {
                        k: (str(v).strip() if v is not None else None)
                        for k, v in row.to_dict().items()
                    }
                    
                    # Add default country_code if not present
                    if "country_code" not in candidate:
                        candidate["country_code"] = "+91"  # Default
                    
                    is_valid, error = validate_candidate(candidate)
                    if not is_valid:
                        skipped += 1
                        errors.append(f"Row {index + 2}: {error}")
                        continue
                    
                    # Check if candidate can be readded/updated
                    can_readd, candidate_id = can_readd_candidate(
                        candidate["email"], candidate["phone"]
                    )
                    
                    if not can_readd:
                        skipped += 1
                        errors.append(f"Row {index + 2}: Cannot add candidate - exists within {THRESHOLD_DAYS} days")
                        continue
                    
                    if candidate_id:
                        update_candidate(candidate_id, candidate)
                        updated += 1
                    else:
                        success = insert_candidate(candidate)
                        if success:
                            inserted += 1
                        else:
                            skipped += 1
                            errors.append(f"Row {index + 2}: Failed to insert (possible duplicate)")
                except Exception as e:
                    skipped += 1
                    errors.append(f"Row {index + 2}: {str(e)}")
            
            return {
                "inserted": inserted,
                "updated": updated,
                "skipped": skipped,
                "errors": errors[:10] if len(errors) > 10 else errors,
                "total_errors": len(errors)
            }
        except Exception as e:
            raise Exception(f"Import failed: {str(e)}")
    
    @staticmethod
    def export_candidates_to_excel(output_file="exported_candidates.xlsx"):
        try:
            rows = get_all_candidates()
            
            if not rows:
                raise Exception("No candidates found to export")
            
            data = [dict(row) for row in rows]
            df = pd.DataFrame(data)
            
            os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
            
            df.to_excel(output_file, index=False)
            return output_file
        except Exception as e:
            raise Exception(f"Export to Excel failed: {str(e)}")
    
    @staticmethod
    def export_candidates_to_csv(output_file="exported_candidates.csv"):
        try:
            rows = get_all_candidates()
            
            if not rows:
                raise Exception("No candidates found to export")
            
            data = [dict(row) for row in rows]
            df = pd.DataFrame(data)
            
            os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
            
            df.to_csv(output_file, index=False, encoding='utf-8')
            return output_file
        except Exception as e:
            raise Exception(f"Export to CSV failed: {str(e)}")
    
    @staticmethod
    def get_csv_sample():
        sample_data = {
            "candidate_name": ["John Doe", "Jane Smith"],
            "skills": ["Python, SQL", "Java, Spring Boot"],
            "phone": ["1234567890", "1234567890"],  # Without country code
            "email": ["john@example.com", "jane@example.com"],
            "location": ["Bangalore", "New York"],
            "available_time": ["9AM-6PM", "10AM-7PM"],
            "status": ["New", "In Progress"],
            "notes": ["Sample note 1", "Sample note 2"],
            "country_code": ["+91", "+1"]  # Country code in separate column
        }
        
        df = pd.DataFrame(sample_data)
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        return csv_buffer.getvalue()

# ============================================================================
# STREAMLIT APPLICATION
# ============================================================================
class TalentTrackApp:
    def __init__(self):
        self.import_export = ImportExport()
        self.STATUSES = list(ALLOWED_STATUS)
        self.COUNTRY_CODES = list(COUNTRY_PHONE_RULES.keys())
        
        # Initialize session state
        if "initialized" not in st.session_state:
            st.session_state.initialized = True
            # Remove existing database to start fresh
            if os.path.exists(DB_PATH):
                os.remove(DB_PATH)
            # Initialize fresh database
            init_db()
    
    def clean_candidate_form(self, values):
        return {
            "candidate_name": values.get("candidate_name", "").strip(),
            "skills": values.get("skills", "").strip() or None,
            "phone": values.get("phone", "").strip(),
            "email": values.get("email", "").strip().lower(),
            "location": values.get("location", "").strip() or None,
            "available_time": values.get("available_time", "").strip() or None,
            "status": values.get("status", "").strip(),
            "notes": values.get("notes", "").strip() or None,
            "country_code": values.get("country_code", "+91")
        }
    
    def normalize_skills_column(self, df):
        if "skill" in df.columns and "skills" not in df.columns:
            df["skills"] = df["skill"]
        
        if "skills" in df.columns and df["skills"].isnull().any():
            df["skills"] = df["skills"].fillna(df.get("skill", ""))
        
        df["skills"] = df["skills"].fillna("").astype(str)
        df["skills"] = df["skills"].str.replace(r"[\[\]\'\"]", " ", regex=True)
        df["skills"] = df["skills"].str.replace(r"[\,\;\|]", " ", regex=True)
        
        return df
    
    def dashboard_page(self):
        st.title("Dashboard")

        rows = get_all_candidates()
        if not rows:
            st.info("No candidates found.")
            return

        df = pd.DataFrame([dict(r) for r in rows])

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Candidates", len(df))
        with col2:
            st.metric("New", len(df[df["status"] == "New"]))
        with col3:
            st.metric("In Progress", len(df[df["status"] == "In Progress"]))
        with col4:
            st.metric("Selected", len(df[df["status"] == "Selected"]))

        # Create status summary for bar chart
        summary = df["status"].value_counts().reset_index()
        summary.columns = ["Status", "Count"]

        # Display bar chart
        st.subheader("Status Distribution")
        st.bar_chart(summary.set_index("Status"), height=500)
    
    def add_candidate_page(self):
        st.title("Add Candidate")
        
        with st.form("add_candidate_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                candidate_name = st.text_input("Candidate Name*")
                country_code = st.selectbox("Country Code*", self.COUNTRY_CODES, index=0)
                phone = st.text_input("Phone* (digits only)", 
                                    placeholder="e.g., 9876543210 for +91",
                                    help="Enter digits only without country code")
                email = st.text_input("Email*")
                location = st.text_input("Location")
            
            with col2:
                skills = st.text_input("Skills (comma separated)")
                available_time = st.text_input("Available Time")
                status = st.selectbox("Status*", self.STATUSES)
                notes = st.text_area("Notes")
            
            st.markdown("*Required fields")
            
            # Add info about supported country codes
            with st.expander("📱 Supported Phone Formats"):
                st.write("**Country Code Rules:**")
                for code, digits in COUNTRY_PHONE_RULES.items():
                    st.write(f"- {code}: {digits} digits")
                st.write("\n**Examples:**")
                st.write("- India (+91): Enter 10 digits (e.g., 9876543210)")
                st.write("- US (+1): Enter 10 digits (e.g., 1234567890)")
                st.write("- UK (+44): Enter 10 digits (e.g., 7123456789)")
            
            submitted = st.form_submit_button("Save Candidate")
        
        if submitted:
            candidate = self.clean_candidate_form({
                "candidate_name": candidate_name,
                "skills": skills,
                "phone": phone,
                "email": email,
                "location": location,
                "available_time": available_time,
                "status": status,
                "notes": notes,
                "country_code": country_code
            })
            
            # Validate candidate
            is_valid, error = validate_candidate(candidate)
            
            if not is_valid:
                st.error(f"❌ {error}")
                return
            
            # Check name existence (non-blocking warning)
            existing_name = find_by_name(candidate["candidate_name"])
            if existing_name:
                st.warning(name_exists_warning(existing_name))
            
            # Check threshold-based logic
            can_readd, candidate_id = can_readd_candidate(candidate["email"], candidate["phone"])
            
            if not can_readd:
                st.error(f"❌ Cannot add candidate - candidate already exists and was added within last {THRESHOLD_DAYS} days")
                return
            
            if candidate_id:
                # Update existing candidate
                update_candidate(candidate_id, candidate)
                st.success(f"✅ Candidate updated successfully! (Existing candidate found, {THRESHOLD_DAYS}+ days passed)")
            else:
                # Insert new candidate
                success = insert_candidate(candidate)
                if success:
                    st.success("✅ Candidate added successfully!")
                else:
                    st.error("❌ Failed to add candidate. Possible duplicate email or phone.")
            
            st.rerun()
    
    def view_search_page(self):
        st.title("View / Search Candidates")
        
        rows = get_all_candidates()
        if not rows:
            st.info("No candidates found.")
            return
        
        df = pd.DataFrame([dict(r) for r in rows])
        df = self.normalize_skills_column(df)
        
        # Search filters
        with st.expander("Search Filters", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                name = st.text_input("Search by Name")
            with col2:
                skills = st.text_input("Search by Skills")
            with col3:
                location = st.text_input("Search by Location")
            
            col4, col5 = st.columns(2)
            with col4:
                status = st.selectbox("Filter by Status", ["All"] + self.STATUSES)
            with col5:
                show_columns = st.multiselect(
                    "Select Columns to Display",
                    options=df.columns.tolist(),
                    default=["candidate_name", "email", "phone", "skills", "status", "location"]
                )
        
        # Apply filters
        if name:
            df = df[df["candidate_name"].str.contains(name, case=False, na=False)]
        
        if skills:
            search = skills.strip().lower()
            df["skills_lower"] = df["skills"].astype(str).str.lower()
            df = df[df["skills_lower"].str.contains(search, case=False, na=False)]
        
        if location:
            df = df[df["location"].str.contains(location, case=False, na=False)]
        
        if status != "All":
            df = df[df["status"] == status]
        
        # Display results
        st.subheader(f"Found {len(df)} candidates")
        
        if not df.empty:
            # Select only the columns to display
            display_df = df[show_columns] if show_columns else df
            
            # Add a download button for filtered results
            csv = display_df.to_csv(index=False)
            st.download_button(
                label="Download Filtered Results (CSV)",
                data=csv,
                file_name="filtered_candidates.csv",
                mime="text/csv"
            )
            
            st.dataframe(display_df, use_container_width=True, height=400)
        else:
            st.info("No candidates match your search criteria.")
    
    def update_candidate_page(self):
        st.title("Update Candidate")
        
        rows = get_all_candidates()
        if not rows:
            st.info("No candidates found.")
            return
        
        df = pd.DataFrame([dict(r) for r in rows])
        df = self.normalize_skills_column(df)
        
        # Create a display name for selection
        df["display_name"] = df["candidate_name"] + " (" + df["email"] + ")"
        
        candidate_id = st.selectbox(
            "Select Candidate",
            df["candidate_id"],
            format_func=lambda x: df[df["candidate_id"] == x]["display_name"].iloc[0] if not df[df["candidate_id"] == x].empty else "Select"
        )
        
        if not candidate_id:
            st.warning("Please select a candidate")
            return
        
        candidate = df[df["candidate_id"] == candidate_id].iloc[0]
        
        # Extract country code and phone digits from existing phone
        current_phone = candidate["phone"]
        country_code = "+91"  # default
        phone_digits = current_phone
        
        for code in self.COUNTRY_CODES:
            if current_phone.startswith(code):
                country_code = code
                phone_digits = current_phone[len(code):]
                break
        
        with st.form("update_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                candidate_name = st.text_input("Candidate Name*", candidate["candidate_name"])
                skills = st.text_input("Skills", candidate["skills"] or "")
                country_code_input = st.selectbox("Country Code*", self.COUNTRY_CODES, 
                                                index=self.COUNTRY_CODES.index(country_code) if country_code in self.COUNTRY_CODES else 0)
                phone = st.text_input("Phone* (digits only)", phone_digits)
                email = st.text_input("Email*", candidate["email"])
            
            with col2:
                location = st.text_input("Location", candidate["location"] or "")
                available_time = st.text_input("Available Time", candidate["available_time"] or "")
                status_index = self.STATUSES.index(candidate["status"]) if candidate["status"] in self.STATUSES else 0
                status = st.selectbox("Status*", self.STATUSES, index=status_index)
                notes = st.text_area("Notes", candidate["notes"] or "")
            
            st.markdown("*Required fields")
            
            col1, col2 = st.columns(2)
            with col1:
                update_btn = st.form_submit_button("Update Candidate")
            with col2:
                cancel_btn = st.form_submit_button("Cancel", type="secondary")
            
            if update_btn:
                updated = self.clean_candidate_form({
                    "candidate_name": candidate_name,
                    "skills": skills,
                    "phone": phone,
                    "email": email,
                    "location": location,
                    "available_time": available_time,
                    "status": status,
                    "notes": notes,
                    "country_code": country_code_input
                })
                
                # Validate candidate
                is_valid, error = validate_candidate(updated)
                
                if not is_valid:
                    st.error(f"❌ {error}")
                    return
                
                # Check name existence (non-blocking warning)
                if candidate_name != candidate["candidate_name"]:
                    existing_name = find_by_name(candidate_name)
                    if existing_name:
                        st.warning(name_exists_warning(existing_name))
                
                update_candidate(candidate_id, updated)
                st.success("✅ Candidate updated successfully!")
                st.rerun()
    
    def delete_candidate_page(self):
        st.title("Delete Candidate")
        
        rows = get_all_candidates()
        if not rows:
            st.info("No candidates found.")
            return
        
        df = pd.DataFrame([dict(r) for r in rows])
        df = self.normalize_skills_column(df)
        
        df["display_name"] = df["candidate_name"] + " (" + df["email"] + ")"
        
        candidate_id = st.selectbox(
            "Select Candidate",
            df["candidate_id"],
            format_func=lambda x: df[df["candidate_id"] == x]["display_name"].iloc[0] if not df[df["candidate_id"] == x].empty else "Select"
        )
        
        if not candidate_id:
            st.warning("Please select a candidate")
            return
        
        candidate = df[df["candidate_id"] == candidate_id].iloc[0]
        
        st.warning("⚠️ You are about to delete the following candidate:")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.write("**Name:**", candidate["candidate_name"])
            st.write("**Email:**", candidate["email"])
            st.write("**Phone:**", candidate["phone"])
            st.write("**Status:**", candidate["status"])
        
        with col2:
            st.write("**Skills:**", candidate["skills"])
            st.write("**Location:**", candidate["location"])
            st.write("**Available Time:**", candidate["available_time"])
            st.write("**Notes:**", candidate["notes"])
        
        col1, col2, col3 = st.columns(3)
        with col2:
            if st.button("❌ Confirm Delete", type="primary"):
                delete_candidate(candidate_id)
                st.success("✅ Candidate deleted successfully!")
                st.rerun()
    
    def import_page(self):
        st.title("Import Candidates")
        
        # File type selection
        file_type = st.radio("Select File Type", ["Excel (.xlsx)", "CSV (.csv)"])
        
        # Template download
        with st.expander("Download Template"):
            if st.button("Download CSV Template"):
                csv_sample = self.import_export.get_csv_sample()
                st.download_button(
                    label="Click to Download CSV Template",
                    data=csv_sample,
                    file_name="candidate_template.csv",
                    mime="text/csv"
                )
            
            st.info(f"""
            **Required Columns:**
            - candidate_name
            - phone (digits only, without country code)
            - email
            - status ({', '.join(ALLOWED_STATUS)})
            - country_code (e.g., +91, +1, +44, etc.)
            
            **Phone Format Rules:**
            - Enter digits only without country code
            - Country code should be in separate 'country_code' column
            - Threshold: Can re-add same candidate after {THRESHOLD_DAYS} days
            
            **Supported Country Codes:**
            """)
            
            for code, digits in COUNTRY_PHONE_RULES.items():
                st.write(f"- {code}: {digits} digits")
            
            st.info("""
            **Optional Columns:**
            - skills
            - location
            - available_time
            - notes
            """)
        
        # File upload
        if file_type == "Excel (.xlsx)":
            uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx", "xls"])
            file_type_code = "excel"
        else:
            uploaded_file = st.file_uploader("Upload CSV File", type=["csv"])
            file_type_code = "csv"
        
        if uploaded_file:
            try:
                # Preview
                st.subheader("File Preview")
                preview = self.import_export.preview_file(uploaded_file, file_type_code)
                preview_df = pd.DataFrame(preview)
                
                # Count valid/invalid
                valid_count = len(preview_df[preview_df["status"] == "✅ Valid"])
                invalid_count = len(preview_df[preview_df["status"] == "❌ Invalid"])
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("✅ Valid Rows", valid_count)
                with col2:
                    st.metric("❌ Invalid Rows", invalid_count)
                
                # Show preview table
                st.dataframe(preview_df, use_container_width=True)
                
                # Show errors if any
                if invalid_count > 0:
                    with st.expander("View Errors"):
                        errors_df = preview_df[preview_df["status"] == "❌ Invalid"]
                        st.dataframe(errors_df[["row_number", "error"]])
                
                # Import button
                if st.button("Import Candidates", type="primary"):
                    with st.spinner("Importing candidates..."):
                        # Reset file pointer
                        uploaded_file.seek(0)
                        result = self.import_export.import_candidates_from_file(uploaded_file, file_type_code)
                    
                    st.success(f"""
                    **Import Summary:**
                    - ✅ Inserted: {result['inserted']}
                    - 🔄 Updated: {result['updated']}
                    - ⏭️ Skipped: {result['skipped']}
                    """)
                    
                    if result['total_errors'] > 0:
                        st.warning(f"Total errors: {result['total_errors']}")
                        with st.expander("View Import Errors"):
                            for error in result['errors']:
                                st.error(error)
            
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
    
    def export_page(self):
        st.title("Export Candidates")
        
        rows = get_all_candidates()
        if not rows:
            st.info("No candidates found to export.")
            return
        
        total_candidates = len(rows)
        st.success(f"✅ Found {total_candidates} candidates ready for export")
        
        # Export options
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Export to Excel")
            excel_filename = st.text_input("Excel filename", "candidates_export.xlsx")
            if st.button("Export to Excel"):
                try:
                    output_file = self.import_export.export_candidates_to_excel(excel_filename)
                    with open(output_file, "rb") as f:
                        st.download_button(
                            label="Download Excel File",
                            data=f,
                            file_name=excel_filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    st.success(f"✅ Exported {total_candidates} candidates to {output_file}")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        
        with col2:
            st.subheader("Export to CSV")
            csv_filename = st.text_input("CSV filename", "candidates_export.csv")
            if st.button("Export to CSV"):
                try:
                    output_file = self.import_export.export_candidates_to_csv(csv_filename)
                    with open(output_file, "rb") as f:
                        st.download_button(
                            label="Download CSV File",
                            data=f,
                            file_name=csv_filename,
                            mime="text/csv"
                        )
                    st.success(f"✅ Exported {total_candidates} candidates to {output_file}")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        
        # Quick download of all data
        st.subheader("Quick Download")
        df = pd.DataFrame([dict(row) for row in rows])
        csv_data = df.to_csv(index=False)
        
        st.download_button(
            label="Download All Data as CSV",
            data=csv_data,
            file_name="all_candidates.csv",
            mime="text/csv"
        )
    
    def run(self):
        # Sidebar Navigation
        st.sidebar.title("TalentTrack")
        st.sidebar.markdown("---")
        
        page = st.sidebar.selectbox(
            "Navigation",
            [
                "Dashboard",
                "Add Candidate",
                "View/Search Candidates",
                "Update Candidate",
                "Delete Candidate",
                "Import Candidates",
                "Export Candidates"
            ]
        )
        
        # Reset button in sidebar
        st.sidebar.markdown("---")
        if st.sidebar.button("🗑️ Reset Database (Demo Only)", type="secondary"):
            if os.path.exists(DB_PATH):
                os.remove(DB_PATH)
            init_db()
            st.sidebar.success("✅ Database reset successfully!")
            st.rerun()
        
        # Page routing
        if page == "Dashboard":
            self.dashboard_page()
        elif page == "Add Candidate":
            self.add_candidate_page()
        elif page == "View/Search Candidates":
            self.view_search_page()
        elif page == "Update Candidate":
            self.update_candidate_page()
        elif page == "Delete Candidate":
            self.delete_candidate_page()
        elif page == "Import Candidates":
            self.import_page()
        elif page == "Export Candidates":
            self.export_page()
        
        # Footer
        st.sidebar.markdown("---")
        st.sidebar.info(f"""
        **TalentTrack v2.0**
        
        Features:
        - ✅ Add, Update, Delete Candidates
        - ✅ Search & Filter
        - ✅ Import Excel/CSV
        - ✅ Export Excel/CSV
        - ✅ Enhanced Phone Validation (8 countries)
        - ✅ Duplicate Detection
        - ✅ Name Existence Warning
        - ✅ {THRESHOLD_DAYS}-day Re-add Threshold
        """)

# ============================================================================
# MAIN APPLICATION
# ============================================================================
if __name__ == "__main__":
    # Page configuration
    st.set_page_config(
        page_title="TalentTrack - Candidate Management",
        page_icon="👨‍💼",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
    .stButton > button {
        width: 100%;
    }
    .stAlert {
        border-radius: 10px;
    }
    .css-1d391kg {
        padding-top: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Run the application
    app = TalentTrackApp()
    app.run()