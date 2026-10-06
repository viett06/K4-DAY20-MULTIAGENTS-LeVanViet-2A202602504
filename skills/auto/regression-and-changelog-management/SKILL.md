---
name: regression-and-changelog-management
description: Use when fixing bugs or completing tasks that require documentation and testing.
---
<body>
- Create `tests/test_regressions.py` immediately after identifying a bug.
- Write one test function per bug fix; ensure the test fails before the fix and passes after.
- Update `CHANGELOG.md` under the `## Unreleased` header for every fix.
- Use the format `- fix(<function_name>): <short description>` for changelog entries.
- Verify that all tests pass and the changelog is updated before submitting the final task.
