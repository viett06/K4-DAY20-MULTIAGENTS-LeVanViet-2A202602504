---
name: verify-output-constraints
description: Use when generating JSON or CSV outputs to ensure compliance with strict formatting rules.
---
<body>
- Explicitly list all formatting rules (e.g., "money in cents", "ISO-8601 UTC", "canonical naming") in a checklist before writing the output file.
- For JSON: verify the presence of required top-level keys (e.g., `meta`, `schema_version`).
- For CSV: verify header names match the specification exactly and check for correct quoting/delimiter usage.
- Validate the final output file by reading the first and last 10 lines to ensure the structure matches the requirements.
