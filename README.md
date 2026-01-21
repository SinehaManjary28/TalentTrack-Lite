# TalentTrack Lite

TalentTrack Lite is a lightweight candidate management system built using Python, Streamlit, and SQLite.  
It replaces Excel-based candidate tracking with a structured database while still supporting Excel import and export workflows.

---

##  Features

- Add candidate details through a web form  
- View and search stored candidates using filters  
- Update existing candidate records  
- Prevent duplicate entries using email and phone checks  
- Import candidate data from Excel with validation  
- Export candidate data from the database to Excel  
- Dashboard displaying total candidate counts and status-wise summary  

---

##  Tech Stack

- **Python**
- **Streamlit** – Web interface  
- **SQLite** – Database  
- **Pandas** – Data processing  
- **OpenPyXL** – Excel import/export  

---

##  Project Structure

```
TalentTrack_Lite/
│
├── streamlit_app.py        # Main Streamlit application
├── db.py                  # SQLite database and CRUD operations
├── validators.py          # Input validation logic
├── import_export.py       # Excel import and export utilities
├── candidate_import_template.xlsx
├── requirements.txt
├── .gitignore
└── README.md
```

---

##  Getting Started

### - Install dependencies

```bash
pip install -r requirements.txt
```
### - Run the application

```bash
streamlit run streamlit_app.py
```

The application will open in your default web browser.

---

##  Excel Import Guidelines

- Use the provided `candidate_import_template.xlsx`
- Ensure required fields such as candidate name, email, phone, and status are filled
- Duplicate records are handled automatically during import

---

##  Data Handling

- Candidate data is stored in a SQLite database
- Email and phone fields are enforced as unique
- Timestamps are maintained for record creation and updates
- Validation is applied before database operations
---

##  Notes

- The SQLite database file is generated locally at runtime
- Database files are excluded from version control using `.gitignore`
- Designed for small teams and internal usage

---

##  License

This project is intended for educational and internal use.
