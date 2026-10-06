# Báo cáo Lab: Self evolving Agentic

## 1. Thông tin nhóm và cấu hình

| Họ tên | Mã sinh viên | Phần đóng góp |
|---|---|---|
| Le Van Viet | 2A202602504 | Cài đặt harness, chạy thí nghiệm, phân tích và báo cáo |

- Mô hình: Google Gemini qua LangChain provider `LAB_MODEL=google_genai:gemini-3.1-flash-lite`, `LAB_TEMPERATURE=0`.
- Deep Agents: `0.7.21`; hệ điều hành: macOS; chạy trực tiếp trong virtualenv.
- `recursion_limit=30` cho các lần chạy chính thức.
- Commit giả thuyết: `afffa8c`; tag `freeze`: `e265e8e`.

## 2. Giả thuyết

- H1: `subagents` có thể tăng điểm ở tác vụ phức tạp nếu tác tử chính giao việc đủ ngữ cảnh cho `explorer` hoặc `reviewer`, nhưng token và thời gian sẽ tăng. Nếu tác tử chính không gọi subagent hoặc giao thiếu luật, điểm có thể không hơn `baseline`.
- H2: `skills-auto` có khả năng cải thiện lỗi quy trình lặp lại, đặc biệt lỗi bỏ sót quy ước Acme hoặc thiếu bước kiểm chứng, nhưng lợi ích trên eval có thể thấp nếu skill không được đọc hoặc quá khớp learning set.
- H3: điểm trên learning set dự kiến cao hơn eval sau khi dùng skill, vì skill được tạo từ lỗi learning set; chênh lệch lớn giữa learn và eval là dấu hiệu quá khớp hoặc nhiễu.

## 3. Làm quen Deep Agents

1. Tác tử mặc định có các công cụ: `ls`, `read_file`, `write_file`, `edit_file`, `delete`, `glob`, `grep`, `execute`, `task`. Công cụ `execute` cho phép chạy lệnh shell trong sandbox.
2. Công cụ `task` dùng để khởi chạy một subagent tạm thời cho tác vụ phức tạp nhiều bước. Subagent chỉ thấy prompt được gửi cho nó, không tự thấy toàn bộ ngữ cảnh của tác tử chính.
3. Một hướng dẫn từ `task`: prompt cho subagent cần đủ chi tiết và nói rõ cần trả về gì. Một hướng dẫn từ `execute`: ưu tiên công cụ `grep`/`glob` thay vì chạy `find` hoặc `grep` trong shell.

## 4. Đường cơ sở và phân loại lỗi

| Tác vụ | Check thất bại | Nhóm lỗi | Bằng chứng |
|---|---|---|---|
| code-learn | visible_suite_passes | B. Không kiểm chứng | `run.json` ghi `GraphRecursionError`; test suite chưa hoàn tất. |
| code-learn | parse_price_all_formats | D. Bỏ sót định dạng | Sai các định dạng tiền đặc biệt như có dấu phẩy, ngoặc âm, ký hiệu tiền. |
| code-learn | rule_type_hints | E. Vi phạm quy ước tổ chức | `RULE: every public function ... has type annotations`. |
| code-learn | rule_regression_tests | E. Vi phạm quy ước tổ chức | `RULE: add tests/test_regressions.py ... at least 3`. |
| code-learn | rule_changelog | E. Vi phạm quy ước tổ chức | `RULE: record each fix in CHANGELOG.md`. |
| data-learn | rule_money_in_cents | E. Vi phạm quy ước tổ chức | `RULE: money values in answer.json are integer cents`. |
| data-learn | rule_meta_block | E. Vi phạm quy ước tổ chức | `RULE: answer.json has an object meta ...`. |
| data-learn | rule_clean_csv | E. Vi phạm quy ước tổ chức | `RULE: write workspace/clean.csv ...`. |
| logs-learn | rule_service_names | E. Vi phạm quy ước tổ chức | `RULE: service names ... lower-case with '-' replaced by '_'`. |
| logs-learn | rule_sorted_errors | E. Vi phạm quy ước tổ chức | `RULE: errors is sorted by service, then by timestamp_utc`. |
| logs-learn | rule_schema_header | E. Vi phạm quy ước tổ chức | `RULE: top-level object has schema_version: 2 and generated_by`. |

Baseline learning đạt technical `12/18` nhưng house rules `0/9`. Nhóm E chiếm đa số, nên lỗi chính không phải hoàn toàn do không giải được tác vụ, mà do bỏ sót quy ước tổ chức ẩn trong check.

## 5. Điều kiện `subagents`

- Đã định nghĩa 3 subagent: `explorer`, `implementer`, `reviewer`.
- `subagent_calls`: learning có `0, 1, 1` lần gọi tương ứng cho `code-learn`, `data-learn`, `logs-learn`; eval có `0, 1, 0`.
- Subagent làm tăng chi phí rõ rệt: mean tokens `152,131`, cao hơn baseline `68,519`.
- Điểm learning tăng từ `0.45` lên `0.51`, nhưng eval giảm từ `0.60` xuống `0.48`. Điều này không ủng hộ H1 trên eval; chi phí tăng không đổi lấy hiệu quả ổn định.

## 6. Self-evolving: skill do curator sinh

Curator sinh 3 skill hợp lệ trong `skills/auto/`:

| Skill | Tổng quát hay riêng? | Đúng hay sai | Độ dài, description, `skills_read` |
|---|---|---|---|
| `syntax-and-lint-check` | Tổng quát cho code/data script | Đúng nhưng khá chung | Ngắn; description hợp lý; `skills_read=0/6`. |
| `verify-output-constraints` | Tổng quát cho JSON/CSV và quy ước output | Đúng, khớp lỗi house rules | Ngắn; description đúng tình huống; `skills_read=0/6`. |
| `regression-and-changelog-management` | Hơi nghiêng về code task | Đúng cho code, ít hữu ích cho data/logs | Ngắn; description hợp lý; `skills_read=0/6`. |

Các skill không chứa dữ liệu eval và `verify_freeze.py` báo OK. Tuy nhiên agent không đọc skill nào trong 6 lần `skills-auto`, nên H2 không được kiểm chứng theo cơ chế mong muốn. Điểm `skills-auto` tương đương baseline trên eval chủ yếu là do hành vi model trong run, không phải bằng chứng skill được áp dụng.

## 7. Kết quả so sánh

```text
| Task | baseline | subagents | skills-auto |
|---|---|---|---|
| code-learn | 3/10 | 5/10 | 5/10 |
| data-learn | 3/8 | 3/8 | 3/8 |
| logs-learn | 6/9 | 6/9 | 6/9 |
| code-eval | 7/11 | 3/11 | 7/11 |
| data-eval | 5/9 | 5/9 | 5/9 |
| logs-eval | 6/10 | 6/10 | 6/10 |
| **Mean score - learning tasks** | 0.45 | 0.51 | 0.51 |
| **Mean score - evaluation tasks** | 0.60 | 0.48 | 0.60 |
| **Mean tokens per run** | 68,519 | 152,131 | 68,452 |
| **Runs that read a skill** | 0/6 | 0/6 | 0/6 |
```

`check_breakdown.py`:

```text
condition     role    technical  house rules  mean tokens  read a skill
baseline      eval     18/18         0/12          63,391      0/3
baseline      learn    12/18         0/9           73,646      0/3
subagents     eval     14/18         0/12         102,633      0/3
subagents     learn    14/18         0/9          201,630      0/3
skills-auto   eval     18/18         0/12          68,645      0/3
skills-auto   learn    14/18         0/9           68,259      0/3
```

## 8. Phân tích

Baseline xử lý tốt các check kỹ thuật trên eval (`18/18`) nhưng không đạt check quy ước (`0/12`). Đây là bằng chứng mạnh rằng tác tử không tự suy ra house rules, dù logic chính vẫn làm được.

Subagents tăng điểm learning ở code task (`3/10` lên `5/10`) nhưng giảm mạnh code eval (`7/11` xuống `3/11`). Các trace cho thấy subagent không được gọi trong code tasks, trong khi data/logs có gọi subagent nhưng không cải thiện house rules. Chi phí token tăng nhiều, đặc biệt `data-learn` dùng `357,272` token.

Skills-auto có learning mean `0.51` và eval mean `0.60`, bằng baseline trên eval. Vì `skills_read=0/6`, không thể kết luận skill tự sinh giúp cải thiện. Cơ chế thất bại có khả năng nằm ở description/kích hoạt skill hoặc tương thích tool-call của model: agent có thư mục skill nhưng không đọc file `SKILL.md`.

Không thấy dấu hiệu overfitting do skill, vì skill không được dùng. Chênh lệch learning/eval của `skills-auto` (`0.51` so với `0.60`) phản ánh nhiễu và độ khó khác nhau giữa task, không phải lợi ích học từ learning set.

## 9. Hạn chế và tính hợp lệ

1. Chỉ có 6 task, nên kết luận có độ bất định cao.
2. Mỗi condition chỉ chạy một lần; model có nhiễu và một số run chạm `GraphRecursionError`.
3. Model Gemini qua LangChain Google có warning về automatic function calling; điều này có thể ảnh hưởng cách trace/tool calls được ghi.
4. `skills_read=0/6`, nên phần self-evolving chỉ đánh giá được việc curator sinh skill và quy trình freeze, chưa đánh giá được lợi ích thực tế của skill.
5. Tất cả run dùng một model duy nhất, không đủ để kết luận về Deep Agents nói chung.

## 10. Kết luận

Harness đã hoàn thiện và pass toàn bộ test offline. Pipeline thí nghiệm đã chạy đủ 3 condition, 6 task, có skill tự sinh, có tag `freeze`, và `verify_freeze.py` báo OK. Kết quả chính: baseline và skills-auto ngang nhau trên eval (`0.60`), subagents tốn token hơn và kém hơn trên eval (`0.48`). Lỗi còn lại chủ yếu là house rules (`0/12` eval ở cả 3 condition).

## Phụ lục

- Lệnh chính đã chạy:
  - `venv/bin/python -m pytest -q`
  - `venv/bin/python -m lab.runner --condition baseline --tasks learn --recursion-limit 30`
  - `venv/bin/python -m lab.runner --condition subagents --tasks learn --recursion-limit 30`
  - `venv/bin/python -m lab.curator`
  - `git commit -m "hypotheses"`
  - `git commit --allow-empty -m "freeze skills" && git tag freeze`
  - `venv/bin/python -m lab.runner --condition baseline --tasks eval --recursion-limit 30`
  - `venv/bin/python -m lab.runner --condition subagents --tasks eval --recursion-limit 30`
  - `venv/bin/python -m lab.runner --condition skills-auto --tasks all --recursion-limit 30`
  - `venv/bin/python scripts/verify_freeze.py`
  - `venv/bin/python -m lab.compare > report/table.md`
  - `venv/bin/python scripts/check_breakdown.py`
- Thử thách mở rộng: chưa thực hiện.
