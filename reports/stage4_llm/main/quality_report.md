# Stage 4 Main Run — Quality Report (Step 2.1)

**작성일**: 2026-06-01
**대상**: `reports/stage4_llm/main/{A,B,C}/{설명,설득}.jsonl` (총 14,580 entries)
**최종 unresolved errors**: **0**
**Validator full-sweep failures**: **0**

## 1. Output line counts (jsonl)

| Stage / Purpose | actual | expected | OK |
|---|---:|---:|:---:|
| A / 설명 | 2,709 | 2,709 | ✓ |
| A / 설득 | 2,151 | 2,151 | ✓ |
| B / 설명 | 2,709 | 2,709 | ✓ |
| B / 설득 | 2,151 | 2,151 | ✓ |
| C / 설명 | 2,709 | 2,709 | ✓ |
| C / 설득 | 2,151 | 2,151 | ✓ |
| **합계** | **14,580** | **14,580** | ✓ |

## 2. Duplicate `essay_id` check

모든 jsonl 에서 `set(essay_id)` 크기 == line 수 → **duplicates = 0**.

## 3. 분리 회계 — output / paid usage / manual recovery

검토자 지적 반영: usage.jsonl 은 paid API 호출만 기록. manual recovery 는
paid 가 아니므로 별도 회계.

| Stage / Purpose | output (jsonl) | paid (usage.jsonl) | manual recovery |
|---|---:|---:|---:|
| A / 설명 | 2,709 | 2,708 | 1 (essay 4381) |
| A / 설득 | 2,151 | 2,151 | 0 |
| B / 설명 | 2,709 | 2,709 | 0 |
| B / 설득 | 2,151 | 2,151 | 0 |
| C / 설명 | 2,709 | 2,709 | 0 |
| C / 설득 | 2,151 | 2,148 | 3 (essays 2205, 10734, 15740) |
| **합계** | **14,580** | **14,576** | **4** |

검산: output (14,580) = paid (14,576) + manual (4) ✓

## 4. `_batch_meta.jsonl` retrieve event 합산

- retrieve events: **10** (3 stages × 2 purposes 기본 + 4 retry/resume)
- Σ `n_succeeded`: **13,339**
- Σ `n_failed`: **28**

(`n_succeeded` 가 14,580 이 아닌 이유: idempotent skip 한 essays 는 retrieve
event 의 `n_succeeded` 에 카운트되지 않음 — 일부 retrieval 이 재시도에서
"이미 done" 으로 처리됨. 최종 output 14,580 이 정답.)

## 5. Manual recovery markers (총 4건)

| Stage | Purpose | essay_id | `_api_revision` |
|---|---|---:|---|
| A | 설명 | 4381 | `manual_recovery_from_markdown_fence:essay4381` |
| C | 설득 | 2205 | `manual_recovery_trim_240:essay2205.task_1` |
| C | 설득 | 10734 | `manual_recovery_trim_240:essay10734.content_3` |
| C | 설득 | 15740 | `manual_recovery_escape_text_quotes:essay15740` |

추적: `grep '"_api_revision":[ ]*"manual_recovery' reports/stage4_llm/main/{A,B,C}/*.jsonl`
→ 4 hits.

세부 절차 및 원본 hash: `reports/stage4_llm/main/C/manual_recovery_2026-06-01.md`.

## 6. Historical attempt errors (resolved + manual recovered)

`reports/stage4_llm/main/errors/errors.jsonl` 누적 row: **28**. 모두 1회차
시도 실패이며 (a) Batch retry 또는 (b) manual recovery 로 해결됨.

| Stage | kind | count |
|---|---|---:|
| A | attempt1_non_json | 10 |
| A | attempt1_validator | 4 |
| C | attempt1_non_json | 7 |
| C | attempt1_validator | 7 |

**Final unresolved errors**: **0** (모든 essay × stage 셀이 정상 jsonl 에 존재).

## 7. Validator full-sweep (gate 4)

전체 14,580 entry 에 대해 `validate_stage_a / b / c` 재실행:
- exceptions raised: **0**

## 8. Stage B null score per-trait

| trait | 설명 null/total (%) | 설득 null/total (%) |
|---|---|---|
| content_1 | 20/2709 (0.7%) | 0/2151 (0.0%) |
| content_2 | 11/2709 (0.4%) | 0/2151 (0.0%) |
| content_3 | 13/2709 (0.5%) | 0/2151 (0.0%) |
| expression_1 | 0/2709 (0.0%) | 0/2151 (0.0%) |
| **expression_2** | **104/2709 (3.8%)** | **64/2151 (3.0%)** |
| organization_1 | 1/2709 (0.0%) | 0/2151 (0.0%) |
| organization_2 | 1/2709 (0.0%) | 0/2151 (0.0%) |
| task_1 | 27/2709 (1.0%) | 1/2151 (0.0%) |

→ 모든 trait 에서 null score **< 10%** (α pilot trigger 임계 미달).
expression_2 가 최고치 3.8% / 3.0% 으로 다른 trait 보다 높지만 임계 안.

## 9. Stage C empty rationale per-trait

| trait | 설명 empty/total (%) | 설득 empty/total (%) |
|---|---|---|
| (모든 trait) | 0/2709 (0.0%) | 0/2151 (0.0%) |

→ Stage C **모든 essay × 모든 trait 에서 rationale text 정상** (smoke 의
axis (c) 동일 기준 통과).

## 10. 종합 결론

- **데이터 완전성**: 14,580 / 14,580 = 100%, 누락 0, 중복 0.
- **검증**: validator full-sweep 0 exception.
- **paid 회계 분리**: paid 14,576 + manual 4 = 14,580.
- **Stage B null rate**: 최고 3.8% (expression_2 설명) — α pilot trigger
  10% 임계 미달.
- **Stage C empty rate**: 0%.
- **다음 단계**: Step 2.2 (`scripts/run_stage5_analysis.py`) — score-level QWK,
  headline V1/V2/V3, alignment Jaccard, axes (f)(g)(h), main contrast 통계.
