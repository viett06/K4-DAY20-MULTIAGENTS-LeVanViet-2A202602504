# Báo cáo Lab: Self evolving Agentic

## 1. Thông tin nhóm và cấu hình

| Họ tên | Mã sinh viên | Phần đóng góp |
|---|---|---|
| Le Van Viet | 2A202602504 | Cài đặt harness, chạy thí nghiệm, phân tích và báo cáo |

- Mô hình: OpenRouter `AZURE_OPENAI_ENDPOINT=https://openrouter.ai/api/v1`, `AZURE_OPENAI_DEPLOYMENT_MODEL=meta/muse-spark-1.3`, `LAB_TEMPERATURE=0`, `recursion_limit=60`.
- Deep Agents: `0.7.21`; hệ điều hành: macOS; chạy trực tiếp trong virtualenv.
- Số lần chạy tác vụ đã dùng / ngân sách: đã chạy 3 baseline learning tasks và 1 subagents run; OpenRouter free tier hết quota ngày (`free-models-per-day`, remaining 0) trước khi hoàn tất pipeline.
- Commit của tag `freeze`: chưa tạo.

## 2. Giả thuyết

- H1 (subagents so với baseline): `subagents` có thể tăng điểm ở tác vụ phức tạp nếu tác tử chính giao việc đủ ngữ cảnh cho `explorer` hoặc `reviewer`, nhưng token và thời gian sẽ tăng. Nếu tác tử chính không gọi subagent hoặc giao thiếu luật, điểm có thể không hơn `baseline`.
- H2 (skills-auto so với baseline): `skills-auto` có khả năng cải thiện các lỗi quy trình lặp lại, đặc biệt lỗi bỏ sót quy ước Acme hoặc thiếu bước kiểm chứng, nhưng lợi ích trên tác vụ đánh giá có thể thấp vì skill do model sinh dễ quá khớp với phản hồi tác vụ học.
- H3 (tác vụ học so với tác vụ đánh giá): điểm trên tác vụ học dự kiến cao hơn tác vụ đánh giá sau khi dùng skill, vì skill được tạo từ lỗi của learning set; chênh lệch lớn giữa learn và eval sẽ là dấu hiệu quá khớp hoặc thiếu tổng quát.

## 3. Làm quen Deep Agents

1. Tác tử mặc định có các công cụ: `ls`, `read_file`, `write_file`, `edit_file`, `delete`, `glob`, `grep`, `execute`, `task`. Công cụ `execute` cho phép chạy lệnh shell trong sandbox.
2. Công cụ `task` dùng để khởi chạy một subagent tạm thời cho tác vụ phức tạp nhiều bước. Subagent mặc định `general-purpose` có cùng công cụ như tác tử chính, nhưng mỗi invocation là stateless: nó chỉ thấy prompt được gửi cho nó và trả về một báo cáo cuối.
3. Một hướng dẫn từ `task`: khi prompt cho subagent cần đặt đầy đủ chi tiết và nói rõ nó phải trả về gì. Một hướng dẫn từ `execute`: ưu tiên công cụ `grep`/`glob` thay vì chạy `find` hoặc `grep` trong shell.

## 4. Đường cơ sở và phân loại lỗi

| Tác vụ | Check thất bại | Nhóm lỗi (A-G) | Bằng chứng |
|---|---|---|---|
| code-learn | visible_suite_passes | B. Không kiểm chứng | `2 failed, 4 passed`; run kết thúc do `GraphRecursionError` với `recursion_limit=15`. |
| code-learn | parse_price_all_formats | D. Bỏ sót định dạng | Sai với `'$1,299.50'`, `'(12.00)'`, `'$1,000,000.00'`. |
| code-learn | rule_type_hints | E. Vi phạm quy ước tổ chức | `RULE: every public function ... has type annotations`. |
| code-learn | rule_regression_tests | E. Vi phạm quy ước tổ chức | `RULE: add tests/test_regressions.py ... at least 3`. |
| code-learn | rule_changelog | E. Vi phạm quy ước tổ chức | `RULE: record each fix in CHANGELOG.md ...`. |
| data-learn | rule_money_in_cents | E. Vi phạm quy ước tổ chức | `RULE: money values in answer.json are integer cents`. |
| data-learn | rule_meta_block | E. Vi phạm quy ước tổ chức | `RULE: answer.json has an object meta ...`. |
| data-learn | rule_clean_csv | E. Vi phạm quy ước tổ chức | `RULE: write workspace/clean.csv ...`. |
| logs-learn | rule_service_names | E. Vi phạm quy ước tổ chức | `RULE: service names ... lower-case with '-' replaced by '_'`. |
| logs-learn | rule_sorted_errors | E. Vi phạm quy ước tổ chức | `RULE: errors is sorted by service, then by timestamp_utc`. |
| logs-learn | rule_schema_header | E. Vi phạm quy ước tổ chức | `RULE: top-level object has schema_version: 2 and generated_by`. |

Nhận xét: nhóm E chiếm đa số trong baseline learning. `scripts/check_breakdown.py` cho baseline learning: technical `12/18`, house rules `0/9`; model xử lý được một phần logic kỹ thuật nhưng bỏ sót quy ước Acme ẩn. Skill checklist về đọc phản hồi `RULE:` và áp dụng house rules có thể phòng ngừa nhóm này.

## 5. Điều kiện `subagents`

- Các subagent đã định nghĩa:
  - `explorer`: đọc đề, README, docstring, dữ liệu mẫu và test; không sửa file.
  - `implementer`: thực hiện thay đổi đã được khoanh vùng và chạy kiểm chứng liên quan.
  - `reviewer`: kiểm tra độc lập kết quả theo đề, README/docstring và quy ước đầu ra.
- `subagent_calls`: mới có `data-learn`; run này lỗi 429 trước khi model chạy nên `subagent_calls=0`, `tool_calls=0`, `tokens=0`.
- Thông tin thiếu hoặc thừa khi giao việc: chưa đánh giá được vì run bị chặn bởi quota OpenRouter free.
- Ảnh hưởng đến token và thời gian: chưa đủ dữ liệu; subagents chưa hoàn tất task nào.

## 6. Self-evolving: skill do curator sinh

- Số lần chạy curator, số skill bị xóa và lý do: chưa chạy được vì OpenRouter free tier hết quota trước Phần 3. Curator cần một lần gọi model thật.

| Skill | Tổng quát hay riêng cho tác vụ học? | Đúng hay sai | Độ dài, `description` và `skills_read` |
|---|---|---|---|
| Chưa sinh | Chưa đánh giá | Chưa đánh giá | Cần chạy `python -m lab.curator` sau khi quota/API khả dụng |

## 7. Kết quả so sánh

```text
| Task | baseline | subagents |
|---|---|---|
| code-learn | 1/10 | - |
| data-learn | 5/8 | 0/8 |
| logs-learn | 6/9 | - |
| **Mean score - learning tasks** | 0.46 | 0.00 |
| **Mean score - evaluation tasks** | - | - |
| **Mean tokens per run** | 38,177 | 0 |
| **Runs that read a skill** | 0/3 | 0/1 |

check_breakdown.py:
condition     role    technical  house rules  mean tokens  read a skill
baseline      learn    12/18         0/9           38,177      0/3
subagents     learn     0/5          0/3                0      0/1
(evaluation rows are hidden until the git tag `freeze` exists)
```

## 8. Phân tích

Số liệu hiện chỉ đủ cho baseline learning và một run subagents bị quota. Baseline đạt trung bình 0.46 trên learning tasks; check kỹ thuật đạt 12/18 nhưng house rules đạt 0/9. Điều này ủng hộ giả thuyết rằng lỗi chính là bỏ sót quy ước tổ chức, không phải hoàn toàn không xử lý được tác vụ.

Chưa thể kết luận về `subagents` hoặc `skills-auto`: `subagents/data-learn` bị `OpenAIRateLimitError 429`, còn curator và eval chưa chạy được.

## 9. Hạn chế và tính hợp lệ

1. Chỉ mới có một phần kết quả vì OpenRouter free tier hết quota ngày trong lúc chạy, nên kết luận chỉ áp dụng cho baseline learning.
2. Thí nghiệm chính của lab chỉ có 3 tác vụ học và 3 tác vụ đánh giá, nên kết luận sau này vẫn có độ bất định cao.
3. Mỗi điều kiện dự kiến chỉ chạy một lần, vì vậy kết quả chịu nhiễu từ mô hình và trạng thái API.

## 10. Kết luận

Phần harness đã được cài đặt và kiểm thử offline. Kết quả baseline học cho thấy lỗi quy ước Acme là nguồn thất bại chính. Cần quota OpenRouter mới hoặc model trả phí/khác để chạy curator, freeze, eval và hoàn tất kết luận chính thức.

## Phụ lục

- Lệnh đã chạy:
  - `venv/bin/python -m pip install -e .`
  - `venv/bin/python -m pytest tests/test_01_provided.py tests/test_02_agent.py tests/test_03_runner.py tests/test_04_curator.py`
  - `venv/bin/python scripts/tour.py`
  - `venv/bin/python -m lab.runner --condition baseline --tasks data-learn --recursion-limit 20`
  - `venv/bin/python -m lab.runner --condition baseline --tasks logs-learn --recursion-limit 20`
  - `venv/bin/python -m lab.runner --condition baseline --tasks code-learn --recursion-limit 15`
  - `venv/bin/python -m lab.runner --condition subagents --tasks data-learn --recursion-limit 10`
  - `venv/bin/python -m lab.compare > report/table.md`
  - `venv/bin/python scripts/check_breakdown.py`
- Thử thách mở rộng: chưa thực hiện.
- Ghi chú khác: `.env` đã chuyển sang OpenRouter Muse Spark 1.3 (`meta/muse-spark-1.3`).
