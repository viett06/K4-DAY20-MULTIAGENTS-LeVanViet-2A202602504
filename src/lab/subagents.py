"""GUIDE Phần 1 - Định nghĩa subagent (tác tử con).   >>> SINH VIÊN CÀI ĐẶT <<<

Pseudo-code: guides/pseudocode/02_subagents.md
Kiểm tra:    pytest tests/test_02_agent.py
"""


def get_subagents() -> list[dict]:
    """Trả về danh sách subagent (ít nhất 2, tên khác nhau).

    Mỗi phần tử là một dict có các khóa bắt buộc:
      "name":          tên duy nhất (chữ thường, có thể có dấu gạch ngang)
      "description":   khi nào tác tử chính nên giao việc cho subagent này (viết như một hướng dẫn hành động)
      "system_prompt": chỉ dẫn cho subagent
    Gợi ý vai trò: explorer (đọc và báo cáo), implementer (thực hiện), reviewer (kiểm tra độc lập).
    """
    return [
        {
            "name": "explorer",
            "description": (
                "Use this subagent before implementation to inspect task instructions, README files, "
                "docstrings, sample data, and tests, then report the relevant requirements without editing files."
            ),
            "system_prompt": (
                "You are a requirements explorer. Read the task files carefully, identify the specification, "
                "edge cases, data-cleaning rules, and validation commands. Do not edit files. Return a concise "
                "report with exact file paths, commands to run, and risks the main agent should check."
            ),
        },
        {
            "name": "implementer",
            "description": (
                "Use this subagent when a scoped code, data, or log-processing change is ready to be made "
                "and the task rules and target files can be passed explicitly."
            ),
            "system_prompt": (
                "You are an implementation specialist. Make only the requested changes, preserve unrelated "
                "files, and run the relevant verification command when possible. Report changed files, commands "
                "run, and any remaining failures."
            ),
        },
        {
            "name": "reviewer",
            "description": (
                "Use this subagent after changes to independently compare the result against the instructions, "
                "README/docstrings, dirty-data rules, and expected output format."
            ),
            "system_prompt": (
                "You are an independent reviewer. Check the completed work against every stated requirement and "
                "likely hidden convention. Do not edit files. Return concrete issues first, then verification "
                "commands and any residual risk."
            ),
        },
    ]
