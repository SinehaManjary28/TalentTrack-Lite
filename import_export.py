import pandas as pd

from db import (
    insert_candidate,
    find_duplicate,
    update_candidate,
    get_all_candidates
)

from validators import validate_candidate


REQUIRED_COLUMNS = [
    "candidate_name",
    "skills",
    "phone",
    "email",
    "location",
    "available_time",
    "status",
    "notes"
]

# -----------------------------------------
# Read Excel or CSV
# -----------------------------------------
def read_file(file):
    file_name = file.name.lower()

    if file_name.endswith(".csv"):
        return pd.read_csv(file, dtype=str)
    elif file_name.endswith((".xls", ".xlsx")):
        return pd.read_excel(file)
    else:
        raise ValueError("Unsupported file format. Upload CSV or Excel.")


# -----------------------------------------
# Normalize dataframe
# - Case insensitive columns
# - Strip spaces
# - Replace NaN with None
# -----------------------------------------
def normalize_dataframe(df):
    df.columns = [col.strip().lower() for col in df.columns]
    df = df.where(pd.notnull(df), None)
    return df


# -----------------------------------------
# Preview file before import
# -----------------------------------------
def preview_excel(file):
    df = read_file(file)
    df = normalize_dataframe(df)

    preview_results = []

    for index, row in df.iterrows():
        candidate = {
            k: (str(v).strip() if v is not None else None)
            for k, v in row.to_dict().items()
        }

        is_valid, error = validate_candidate(candidate)

        preview_results.append({
            "row_number": index + 2,  # header + 1
            "status": "valid" if is_valid else "invalid",
            "error": error
        })

    return preview_results


# -----------------------------------------
# Import candidates from Excel / CSV
# -----------------------------------------
def import_candidates_from_excel(file):
    df = read_file(file)
    df = normalize_dataframe(df)

    inserted, updated, skipped = 0, 0, 0

    for _, row in df.iterrows():
        candidate = {
            k: (str(v).strip() if v is not None else None)
            for k, v in row.to_dict().items()
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

    return {
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped
    }


# -----------------------------------------
# Export candidates to Excel
# -----------------------------------------
def export_candidates_to_excel(output_file="exported_candidates.xlsx"):
    rows = get_all_candidates()

    data = [dict(row) for row in rows]
    df = pd.DataFrame(data)

    df.to_excel(output_file, index=False)

    return output_file
