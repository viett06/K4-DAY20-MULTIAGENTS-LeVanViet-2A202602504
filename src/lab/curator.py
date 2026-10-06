"""GUIDE Phần 3 - Người tuyển chọn skill (skill curator): tự viết skill từ các lần chạy thất bại.   >>> SINH VIÊN CÀI ĐẶT curate_skills <<<

Pseudo-code: guides/pseudocode/04_curator.md
Kiểm tra:    pytest tests/test_04_curator.py
Chạy thật:   python -m lab.curator
"""
import re
import json
from pathlib import Path

from .model import make_model
from .tasks import ROOT, eval_markers   # có sẵn: định danh của tác vụ đánh giá, tính lúc chạy

# ---- CÓ SẴN, KHÔNG SỬA: kiểm tra và tách khối skill (phần dễ sai và liên quan bảo mật) ----------------
SAFE_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def validate_skill(text: str, expected_name: str | None = None) -> list[str]:
    """Kiểm tra nội dung một SKILL.md. Trả về danh sách vấn đề (rỗng = hợp lệ).

    Quy tắc: có khối YAML frontmatter; `name` chữ thường/số/gạch ngang (tối đa 64 ký tự) và bằng `expected_name`
    nếu được truyền; có `description` (tối đa 1024 ký tự); phần thân tối đa 80 dòng; không chứa chuỗi nào của
    `eval_markers()`. Quy tắc về `name` cũng là biện pháp bảo mật: tên khối do LLM sinh ra được dùng để tạo
    đường dẫn, nên `../evil` không được lọt qua.
    """
    problems = []
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text.strip() + "\n", re.S)
    if not m:
        return ["missing YAML frontmatter"]
    front, body = m.groups()
    name = re.search(r"^name:\s*(.+)$", front, re.M)
    desc = re.search(r"^description:\s*(.+)$", front, re.M)
    n = name.group(1).strip() if name else ""
    if not SAFE_NAME.fullmatch(n) or len(n) > 64:
        problems.append("invalid name")
    elif expected_name is not None and n != expected_name:
        problems.append("name differs from the block name")
    if not desc or len(desc.group(1).strip()) > 1024:
        problems.append("missing or too long description")
    if len(body.strip().splitlines()) > 80:
        problems.append("body longer than 80 lines")
    low = text.lower()
    for marker in eval_markers():
        if marker in low:
            problems.append(f"mentions evaluation material: {marker}")
    return problems


def parse_skill_blocks(reply: str) -> list[tuple[str, str]]:
    """Tách câu trả lời của LLM thành danh sách (name, nội dung SKILL.md).

    Khuôn dạng: `=== SKILL: <name> ===` ... `=== END ===`. Một khối kết thúc ở điểm nào đến trước trong ba điểm:
    `=== END ===`, tiêu đề `=== SKILL:` kế tiếp, hoặc cuối văn bản (LLM đôi khi quên dòng END).
    """
    pattern = re.compile(r"^=== SKILL: (\S+) ===[ \t]*\n(.*?)(?=^=== END ===|^=== SKILL: |\Z)", re.S | re.M)
    return [(name, text.strip()) for name, text in pattern.findall(str(reply))]
# --------------------------------------------------------------------------------------------------


def curate_skills(results_dir="results", source_condition="baseline", out_dir=None, model=None, max_skills: int = 3) -> list[Path]:
    """Đọc các lần chạy của TÁC VỤ HỌC (role == "learn") trong `source_condition`, nhờ LLM viết skill, ghi file.

    Các bước: nạp run.json + trace.md -> (nếu không có check nào thất bại: in cảnh báo và trả về [] mà KHÔNG gọi LLM)
    -> dựng prompt -> model.invoke(prompt) -> parse_skill_blocks -> validate_skill(text, expected_name=name)
    -> ghi `<out_dir>/<name>/SKILL.md`. Mặc định `out_dir` = <gốc lab>/skills/auto (dùng `ROOT` từ lab.tasks).
    Giữ tối đa `max_skills` skill hợp lệ; skill không hợp lệ bị bỏ qua.
    Prompt chứa, với mỗi check thất bại, TÊN và trường `detail` (lời nhận xét của bot đánh giá: phát biểu quy tắc bị vi phạm)
    cùng phần cuối của vết (trace). Với tác vụ học, `detail` chỉ phát biểu quy tắc, không chứa đáp án.
    Tuyệt đối KHÔNG đưa dữ liệu của tác vụ đánh giá (role == "eval") vào prompt.
    model mặc định: make_model() (lab.model).
    Trả về: danh sách đường dẫn SKILL.md đã ghi.
    """
    results_path = Path(results_dir)
    out_path = Path(out_dir) if out_dir is not None else ROOT / "skills" / "auto"

    runs = []
    for run_file in sorted((results_path / source_condition).glob("*/run.json")):
        try:
            record = json.loads(run_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if record.get("role") != "learn":
            continue
        failed = [
            {"name": check.get("name", ""), "detail": check.get("detail", "")}
            for check in record.get("checks", [])
            if not check.get("passed")
        ]
        trace_file = run_file.with_name("trace.md")
        trace = trace_file.read_text(encoding="utf-8")[-6000:] if trace_file.exists() else ""
        runs.append({"task": record.get("task", run_file.parent.name), "failed": failed, "trace": trace})

    if not any(run["failed"] for run in runs):
        print("không có check thất bại ở tác vụ học")
        return []

    prompt = _build_prompt(runs, max_skills)
    chat_model = model or make_model()
    reply = _content_text(chat_model.invoke(prompt).content)

    written = []
    seen = set()
    for name, text in parse_skill_blocks(str(reply)):
        if len(written) >= max_skills:
            break
        name, text = _normalize_skill_block(name, text)
        if name in seen:
            continue
        seen.add(name)
        if validate_skill(text, expected_name=name):
            continue
        skill_dir = out_path / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        path = skill_dir / "SKILL.md"
        path.write_text(text.strip() + "\n", encoding="utf-8")
        written.append(path)
    return written


def _content_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            str(item.get("text", ""))
            if isinstance(item, dict) and item.get("type") == "text"
            else str(item)
            for item in content
        )
    return str(content)


def _normalize_skill_block(name: str, text: str) -> tuple[str, str]:
    raw = name.strip().lower()
    if not re.fullmatch(r"[a-z0-9_-]+", raw):
        return name, text
    safe = raw.replace("_", "-")
    text = re.sub(r"(?m)^name:\s*.+$", f"name: {safe}", text, count=1)
    return safe, text


def _build_prompt(runs: list[dict], max_skills: int) -> str:
    parts = [
        "You write SKILL files for a programming and data-analysis agent.",
        "Below are failed checks from learning tasks only, with evaluator feedback and the end of the main trace.",
        f"Find general process mistakes and write at most {max_skills} short skills that help on new tasks of the same kinds.",
        "",
        "Rules:",
        "- Keep skills general: do not mention task ids, task-specific file names, answers, or exact numeric results.",
        "- Each skill must have YAML frontmatter with name and description.",
        "- The description must say when to use the skill.",
        "- The body must be imperative checklist guidance, at most 40 lines.",
        "- Output exactly this format for each skill:",
        "=== SKILL: <name> ===",
        "---",
        "name: <name>",
        "description: <when to use>",
        "---",
        "<body>",
        "=== END ===",
    ]
    for run in runs:
        if not run["failed"]:
            continue
        parts.extend(["", f"LEARNING RUN: {run['task']}", "FAILED CHECKS:"])
        for check in run["failed"]:
            parts.append(f"- {check['name']}: {check['detail']}")
        parts.extend(["TRACE TAIL:", run["trace"]])
    return "\n".join(parts)


if __name__ == "__main__":
    for p in curate_skills():
        print("wrote", p)
