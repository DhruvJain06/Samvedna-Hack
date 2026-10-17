# Nightly Trust Test Report — {{DATE}}

| Role | Action | Outcome |
|------|--------|---------|
| commanding_officer | open_individual_case | {{co_open_individual}} |
| commanding_officer | view_small_unit | {{co_view_small_unit}} |
| auditor | change_verdict | {{au_change_verdict}} |
| auditor | download_raw_records | {{au_download_raw}} |
| welfare_officer | view_out_of_scope_unit | {{wo_out_of_scope}} |
| personnel | read_other_self_assessment | {{pers_read_other}} |

**Overall:** {{overall_outcome}}

Generated at {{timestamp}}Z by Airflow DAG `trust_tests`.
Full run logs: [TinyFish Run](https://agent.tinyfish.ai/runs/{{run_id}})
