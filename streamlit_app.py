# talenttrack_app.py - Complete TalentTrack Application with CSV Support
import os
import streamlit as st
import pandas as pd
import sqlite3
import uuid
import re
from datetime import datetime
from io import StringIO

# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================
class Database:
    def __init__(self):
        self.DB_PATH = "talenttrack.db"
        self.init_db()
    
    def get_connection(self):
        conn = sqlite3.connect(self.DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_timestamp(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def init_db(self):
        conn = self.get_connection()
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
    
    def insert_candidate(self, data):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        candidate_id = str(uuid.uuid4())
        timestamp = self.get_timestamp()
        
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
    
    def get_all_candidates(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM candidates")
        rows = cursor.fetchall()
        
        conn.close()
        return rows
    
    def find_duplicate(self, email, phone):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM candidates
            WHERE email = ? OR phone = ?
        """, (email, phone))
        
        row = cursor.fetchone()
        conn.close()
        return row
    
    def update_candidate(self, candidate_id, updated_data):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        timestamp = self.get_timestamp()
        
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
    
    def delete_candidate(self, candidate_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "DELETE FROM candidates WHERE candidate_id = ?",
            (candidate_id,)
        )
        
        conn.commit()
        conn.close()

# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================
class Validator:
    ALLOWED_STATUS = {"New", "In Progress", "Selected", "Rejected"}
    
    @staticmethod
    def validate_required_fields(candidate):
        required_fields = ["candidate_name", "email", "phone", "status"]
        
        for field in required_fields:
            if field not in candidate or not str(candidate[field]).strip():
                return False, f"{field.replace('_', ' ').title()} is required."
        
        return True, None
    
    @staticmethod
    def validate_email(email):
        email = email.strip().lower()
        email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        
        if not re.match(email_regex, email):
            return False, "Invalid email format."
        
        return True, None
    
    @staticmethod
    def validate_phone(phone):
        if not phone:
            return False, "Phone number is required."
        
        phone = phone.strip()
        
        if not phone.startswith("+91"):
            return False, "Phone number must start with +91."
        
        if len(phone) != 13:
            return False, "Phone number must be in +91XXXXXXXXXX format."
        
        number_part = phone[3:]
        if not number_part.isdigit():
            return False, "Phone number must contain only digits after +91."
        
        return True, None
    
    @staticmethod
    def validate_status(status):
        if status not in Validator.ALLOWED_STATUS:
            return False, f"Status must be one of {', '.join(Validator.ALLOWED_STATUS)}."
        
        return True, None
    
    @staticmethod
    def validate_candidate(candidate):
        is_valid, error = Validator.validate_required_fields(candidate)
        if not is_valid:
            return False, error
        
        is_valid, error = Validator.validate_email(candidate["email"])
        if not is_valid:
            return False, error
        
        is_valid, error = Validator.validate_phone(candidate["phone"])
        if not is_valid:
            return False, error
        
        is_valid, error = Validator.validate_status(candidate["status"])
        if not is_valid:
            return False, error
        
        return True, None

# ============================================================================
# IMPORT/EXPORT FUNCTIONS
# ============================================================================
class ImportExport:
    @staticmethod
    def normalize_dataframe(df):
        df.columns = [str(col).strip().lower() for col in df.columns]
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
            validator = Validator()
            
            for index, row in df.iterrows():
                candidate = {
                    k: (str(v).strip() if v is not None else None)
                    for k, v in row.to_dict().items()
                }
                
                is_valid, error = validator.validate_candidate(candidate)
                
                preview_results.append({
                    "row_number": index + 2,
                    "status": "✅ Valid" if is_valid else "❌ Invalid",
                    "error": error if error else "No errors"
                })
            
            return preview_results
        except Exception as e:
            raise Exception(f"Preview failed: {str(e)}")
    
    @staticmethod
    def import_candidates_from_file(file, file_type, db):
        try:
            df = ImportExport.read_file(file, file_type)
            df = ImportExport.normalize_dataframe(df)
            
            inserted = 0
            updated = 0
            skipped = 0
            errors = []
            validator = Validator()
            
            for index, row in df.iterrows():
                try:
                    candidate = {
                        k: (str(v).strip() if v is not None else None)
                        for k, v in row.to_dict().items()
                    }
                    
                    is_valid, error = validator.validate_candidate(candidate)
                    if not is_valid:
                        skipped += 1
                        errors.append(f"Row {index + 2}: {error}")
                        continue
                    
                    existing = db.find_duplicate(candidate["email"], candidate["phone"])
                    
                    if existing:
                        db.update_candidate(existing["candidate_id"], candidate)
                        updated += 1
                    else:
                        success = db.insert_candidate(candidate)
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
    def export_candidates_to_excel(db, output_file="exported_candidates.xlsx"):
        try:
            rows = db.get_all_candidates()
            
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
    def export_candidates_to_csv(db, output_file="exported_candidates.csv"):
        try:
            rows = db.get_all_candidates()
            
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
            "phone": ["+911234567890", "+919876543210"],
            "email": ["john@example.com", "jane@example.com"],
            "location": ["Bangalore", "Mumbai"],
            "available_time": ["9AM-6PM", "10AM-7PM"],
            "status": ["New", "In Progress"],
            "notes": ["Sample note 1", "Sample note 2"]
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
        self.db = Database()
        self.validator = Validator()
        self.import_export = ImportExport()
        self.STATUSES = ["New", "In Progress", "Selected", "Rejected"]
        
        # Initialize session state
        if "initialized" not in st.session_state:
            st.session_state.initialized = True
            if os.path.exists("talenttrack.db"):
                os.remove("talenttrack.db")
            self.db.init_db()
    
    def clean_candidate_form(self, values):
        return {
            "candidate_name": values.get("candidate_name", "").strip(),
            "skills": values.get("skills", "").strip() or None,
            "phone": values.get("phone", "").strip(),
            "email": values.get("email", "").strip().lower(),
            "location": values.get("location", "").strip() or None,
            "available_time": values.get("available_time", "").strip() or None,
            "status": values.get("status", "").strip(),
            "notes": values.get("notes", "").strip() or None
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
        st.title("📊 Dashboard")
        
        rows = self.db.get_all_candidates()
        if not rows:
            st.info("No candidates found.")
            return
        
        df = pd.DataFrame([dict(r) for r in rows])
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Candidates", len(df))
        with col2:
            st.metric("New", len(df[df["status"] == "New"]))
        with col3:
            st.metric("In Progress", len(df[df["status"] == "In Progress"]))
        with col4:
            st.metric("Selected", len(df[df["status"] == "Selected"]))
        
        # Status Summary
        if "status" in df.columns:
            summary = df["status"].value_counts().reset_index()
            summary.columns = ["Status", "Count"]
            st.subheader("Status Distribution")
            st.table(summary)
        
        # Recent Candidates
        st.subheader("Recent Candidates")
        if "created_at" in df.columns:
            recent_df = df.sort_values("created_at", ascending=False).head(10)
        else:
            recent_df = df.head(10)
        st.dataframe(recent_df[["candidate_name", "email", "phone", "status", "location"]])
    
    def add_candidate_page(self):
        st.title("➕ Add Candidate")
        
        with st.form("add_candidate_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                candidate_name = st.text_input("Candidate Name*")
                phone = st.text_input("Phone* (format: +91XXXXXXXXXX)")
                email = st.text_input("Email*")
                location = st.text_input("Location")
            
            with col2:
                skills = st.text_input("Skills (comma separated)")
                available_time = st.text_input("Available Time")
                status = st.selectbox("Status*", self.STATUSES)
                notes = st.text_area("Notes")
            
            st.markdown("*Required fields")
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
            })
            
            valid, error = self.validator.validate_candidate(candidate)
            if not valid:
                st.error(f"❌ {error}")
                return
            
            existing = self.db.find_duplicate(candidate["email"], candidate["phone"])
            if existing:
                st.warning("⚠️ Duplicate candidate found!")
                with st.expander("View Existing Candidate"):
                    st.json(dict(existing))
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Update Existing Candidate"):
                        self.db.update_candidate(existing["candidate_id"], candidate)
                        st.success("✅ Candidate updated successfully!")
                        st.rerun()
                with col2:
                    if st.button("Cancel"):
                        st.rerun()
                return
            
            success = self.db.insert_candidate(candidate)
            if success:
                st.success("✅ Candidate added successfully!")
                st.rerun()
            else:
                st.error("❌ Failed to add candidate. Possible duplicate email or phone.")
    
    def view_search_page(self):
        st.title("🔍 View / Search Candidates")
        
        rows = self.db.get_all_candidates()
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
                label="📥 Download Filtered Results (CSV)",
                data=csv,
                file_name="filtered_candidates.csv",
                mime="text/csv"
            )
            
            st.dataframe(display_df, use_container_width=True, height=400)
        else:
            st.info("No candidates match your search criteria.")
    
    def update_candidate_page(self):
        st.title("✏️ Update Candidate")
        
        rows = self.db.get_all_candidates()
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
        
        with st.form("update_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                candidate_name = st.text_input("Candidate Name*", candidate["candidate_name"])
                skills = st.text_input("Skills", candidate["skills"] or "")
                phone = st.text_input("Phone*", candidate["phone"])
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
                })
                
                valid, error = self.validator.validate_candidate(updated)
                if not valid:
                    st.error(f"❌ {error}")
                    return
                
                self.db.update_candidate(candidate_id, updated)
                st.success("✅ Candidate updated successfully!")
                st.rerun()
    
    def delete_candidate_page(self):
        st.title("🗑️ Delete Candidate")
        
        rows = self.db.get_all_candidates()
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
                self.db.delete_candidate(candidate_id)
                st.success("✅ Candidate deleted successfully!")
                st.rerun()
    
    def import_page(self):
        st.title("📤 Import Candidates")
        
        # File type selection
        file_type = st.radio("Select File Type", ["Excel (.xlsx)", "CSV (.csv)"])
        
        # Template download
        with st.expander("📋 Download Template"):
            if st.button("Download CSV Template"):
                csv_sample = self.import_export.get_csv_sample()
                st.download_button(
                    label="Click to Download CSV Template",
                    data=csv_sample,
                    file_name="candidate_template.csv",
                    mime="text/csv"
                )
            
            st.info("""
            **Required Columns:**
            - candidate_name
            - phone (format: +91XXXXXXXXXX)
            - email
            - status (New, In Progress, Selected, Rejected)
            
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
                st.subheader("📄 File Preview")
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
                if st.button("🚀 Import Candidates", type="primary"):
                    with st.spinner("Importing candidates..."):
                        # Reset file pointer
                        uploaded_file.seek(0)
                        result = self.import_export.import_candidates_from_file(uploaded_file, file_type_code, self.db)
                    
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
        st.title("📥 Export Candidates")
        
        rows = self.db.get_all_candidates()
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
            if st.button("📊 Export to Excel"):
                try:
                    output_file = self.import_export.export_candidates_to_excel(self.db, excel_filename)
                    with open(output_file, "rb") as f:
                        st.download_button(
                            label="⬇️ Download Excel File",
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
            if st.button("📄 Export to CSV"):
                try:
                    output_file = self.import_export.export_candidates_to_csv(self.db, csv_filename)
                    with open(output_file, "rb") as f:
                        st.download_button(
                            label="⬇️ Download CSV File",
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
            label="⬇️ Download All Data as CSV",
            data=csv_data,
            file_name="all_candidates.csv",
            mime="text/csv"
        )
    
    def run(self):
        # Sidebar Navigation
        st.sidebar.title("🎯 TalentTrack")
        st.sidebar.markdown("---")
        
        page = st.sidebar.selectbox(
            "Navigation",
            [
                "📊 Dashboard",
                "➕ Add Candidate",
                "🔍 View/Search Candidates",
                "✏️ Update Candidate",
                "🗑️ Delete Candidate",
                "📤 Import Candidates",
                "📥 Export Candidates"
            ]
        )
        
        # Page routing
        if page == "📊 Dashboard":
            self.dashboard_page()
        elif page == "➕ Add Candidate":
            self.add_candidate_page()
        elif page == "🔍 View/Search Candidates":
            self.view_search_page()
        elif page == "✏️ Update Candidate":
            self.update_candidate_page()
        elif page == "🗑️ Delete Candidate":
            self.delete_candidate_page()
        elif page == "📤 Import Candidates":
            self.import_page()
        elif page == "📥 Export Candidates":
            self.export_page()
        
        # Footer
        st.sidebar.markdown("---")
        st.sidebar.info("""
        **TalentTrack v1.0**
        
        Features:
        - ✅ Add, Update, Delete Candidates
        - ✅ Search & Filter
        - ✅ Import Excel/CSV
        - ✅ Export Excel/CSV
        - ✅ Phone/Email Validation
        - ✅ Duplicate Detection
        """)

# ============================================================================
# MAIN APPLICATION
# ============================================================================
if __name__ == "__main__":
    # Page configuration
    st.set_page_config(
        page_title="TalentTrack - Candidate Management",
        page_icon="👥",
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