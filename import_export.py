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
def normalize_dataframe(df):
    # Make column names lowercase and strip spaces
    df.columns = [col.strip().lower() for col in df.columns]

    # Replace NaN with None
    df = df.where(pd.notnull(df), None)

    return df
def preview_excel(file_path):
    df = pd.read_excel(file_path)
    df = normalize_dataframe(df)

    preview_results = []

    for index, row in df.iterrows():
        candidate = {
    k: (str(v).strip() if v is not None else None)
    for k, v in row.to_dict().items()
}


        is_valid, error = validate_candidate(candidate)

        preview_results.append({
            "row_number": index + 2,  # Excel row number (header + 1)
            "status": "valid" if is_valid else "invalid",
            "error": error
        })

    return preview_results
def import_candidates_from_excel(file_path):
    df = pd.read_excel(file_path)
    df = normalize_dataframe(df)

    inserted = 0
    updated = 0
    skipped = 0

    for _, row in df.iterrows():
        candidate = {
    k: (str(v).strip() if v is not None else None)
    for k, v in row.to_dict().items()
}


        # Validate candidate
        is_valid, error = validate_candidate(candidate)
        if not is_valid:
            skipped += 1
            continue

        # Duplicate check (email OR phone)
        existing = find_duplicate(candidate["email"], candidate["phone"])

        if existing:
            update_candidate(existing["candidate_id"], candidate)
            updated += 1
        else:
            success = insert_candidate(candidate)
            if success:
                inserted += 1
            else:
                skipped += 1

    return {
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped
    }
def export_candidates_to_excel(output_file="exported_candidates.xlsx"):
    rows = get_all_candidates()

    data = [dict(row) for row in rows]
    df = pd.DataFrame(data)

    df.to_excel(output_file, index=False)

    return output_file
if __name__ == "__main__":
    print("=== PREVIEW MODE ===")
    preview = preview_excel("candidates.xlsx")
    for row in preview:
        print(row)

    print("\n=== IMPORT MODE ===")
    summary = import_candidates_from_excel("candidates.xlsx")
    print(summary)

    print("\n=== EXPORT MODE ===")
    file = export_candidates_to_excel()
    print(f"Exported to {file}")
