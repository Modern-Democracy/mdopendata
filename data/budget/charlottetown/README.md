# Charlottetown Budget Source Profiles

This directory contains discovery-only profiles for the 2024/2025, 2025/2026, and 2026/2027 City of Charlottetown financial-plan PDFs.

Each annual directory contains:

- `source_profile.json`: document metadata, source hash, and profile counts
- `profile_page_inventory.json` and `.csv`: one record per PDF page
- `profile_table_inventory.json` and `.csv`: one record per detected financial table or project-profile candidate
- `profile-raw-pages/`: selected embedded or OCR text used by the profiler
- `profile-ocr-pages/`: OCR fallback text where the embedded text layer was insufficient

Run one profile with:

```powershell
python scripts/profile-charlottetown-budget-pdf.py `
  --pdf "docs/charlottetown/budget/2026-2027 Financial Plan Capital and Operating Budgets.pdf" `
  --document-key 2026-2027 `
  --out data/budget/charlottetown/2026-2027
```

These artifacts do not contain normalized financial facts. Table families and continuation groups are discovery candidates and require review before extraction or import.
