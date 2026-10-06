---
name: syntax-and-lint-check
description: Use before executing any script to prevent runtime errors and ensure code quality.
---
<body>
- Run `python3 -m py_compile <script_name>.py` to verify syntax before execution.
- Check for common errors: unclosed strings, missing parentheses, or mismatched indentation.
- If the task involves data processing, add a dry-run print statement to verify the first few rows of output before generating the full file.
- Ensure all imports are at the top of the file and standard libraries are used where possible.
