# Redaction note — pre-specified documents (public package)

익명 심사를 위해 사전 명세 문서 중 신원 포함 2종에서 (i) 합의 참여자/감사 절 1블록을 제거하고 (ii) 본문에 산재한 신원 문자열(이름·기관 라벨)을 치환하였다. 조작적 정의·결정 규칙·수치는 변경하지 않았으며, 치환 0건 섹션은 원본과 바이트 동일함을 아래 섹션 해시로 기계 검증할 수 있다. main_contrast는 신원 정보가 없어 원본 바이트 동일로 공개되며, 공개본 해시가 곧 사전 명세 앵커 해시이다.

신원 포함 원본 2종(SHA 아래 명시)은 DKIM·타임스탬프로 앵커되어 비공개 보관 중이며, **게재 확정 시 공개**한다. 그 시점에 원본–공개본 전체 diff로 본 문서의 모든 주장을 완전 검증할 수 있다.

증거 사슬: 원본 SHA(앵커됨) → 본 redaction(결정론적 스크립트 수행, 제거·치환 내역 본 문서에 명세) → 공개본 SHA.

## decision_table_preregistered_v1.1.md

- 원본(내부, 비공개) SHA-256: `490df99a0b495028a166170ab7c31b59807ba0c4fd82d71f3908ecb7586d101f`
- 익명 공개본 SHA-256: `891282498a490c6aa2fc9355ffdbf40ac13850adc7178913ccfdee53a53672c9`
- 제거: 참여자/감사 절 1블록(원본 lines 20–33, 1220 bytes)
- 치환: 신원 문자열 총 15건 (이름·기관 라벨 한정, 섹션별 아래 표)

| 섹션(첫 행) | 치환 | 판정 |
|---|---|---|
| # Pre-registered Messick Decision Table | 3건 | 치환으로 해시 상이(예상) |
| ## 1. 배경 | 0건 | 바이트 동일 `42f0be2fe65d0e46…` |
| ### 1.1 Indeterminate novel category 정당화 (v1.1 post-V1/V2/V3 verificat | 0건 | 바이트 동일 `9a3dc78e527ccfa1…` |
| **정당화**: | 0건 | 바이트 동일 `0729e9bec62999bc…` |
| ## 2. 결정 규칙 (v2.3 §4.5.2 사전등록 원문) | 0건 | 바이트 동일 `caf81cc4ee0580c8…` |
| ## 3. 조작화 | 0건 | 바이트 동일 `0de5290a54c7317e…` |
| ### 3.1 "지속적으로 나타나지 않음" (UR 조건) | 0건 | 바이트 동일 `e285793803ededcd…` |
| **임계치 정당화 (v1.1 post-V1/V2/V3 verification 명시)**: | 0건 | 바이트 동일 `50103552ca667cbe…` |
| ### 3.2 "정당화하지 않음" (CIV 조건) | 0건 | 바이트 동일 `968de1f1f182adcb…` |
| ### 3.3 "상충하여 귀속 불가" (Indeterminate 조건) | 0건 | 바이트 동일 `b984cb76ebdc1b03…` |
| ### 3.4 "수렴" (Aligned 조건) | 0건 | 바이트 동일 `4e8f06b102393ebf…` |
| ## 4. 범주 간 우선순위 | 0건 | 바이트 동일 `580c679b8813cd04…` |
| ## 5. Stage 5 실행 시 체크리스트 (internal consensus scope) | 2건 | 치환으로 해시 상이(예상) |
| ## 6. 통계 review decline + 부록 D self-audit (v1.0 audit trail) | 0건 | 바이트 동일 `1bd602f5d627b267…` |
| **Event log**: | 4건 | 치환으로 해시 상이(예상) |
| ### 2026-05-15 V1/V2/V3 reference verification 후속 (v1.1) | 0건 | 바이트 동일 `55c7d28b696cdeda…` |
| ## 7. 버전 이력 | 6건 | 치환으로 해시 상이(예상) |

## family_rubric_mapping_preregistered_v1.2.md

- 원본(내부, 비공개) SHA-256: `5f8e5a72c12e33b01dfe49c08e3686ca89c383ea37000af224fd88fbb614139c`
- 익명 공개본 SHA-256: `25fa9a92e8c68c6a826b82da7ebf9a9dc197e25f24aec4db2d6910238e1f751a`
- 제거: 참여자/감사 절 1블록(원본 lines 18–30, 899 bytes)
- 치환: 신원 문자열 총 18건 (이름·기관 라벨 한정, 섹션별 아래 표)

| 섹션(첫 행) | 치환 | 판정 |
|---|---|---|
| # Pre-registered Feature Family ↔ Rubric 영역 매핑 | 2건 | 치환으로 해시 상이(예상) |
| ## 1. 배경 | 1건 | 치환으로 해시 상이(예상) |
| ## 2. 매핑 표 (v2.3 부록 C 원문) | 0건 | 바이트 동일 `7efa8775114ff970…` |
| **표 footer (v1.0+ 명료화; v1.1에서 그대로 유지)**: | 2건 | 치환으로 해시 상이(예상) |
| ## 3. 매핑 근거 (이론 기반) | 0건 | 바이트 동일 `b77f24fb314bcde3…` |
| ### 3.1 `1A` task — 과제 이해·반영 | 0건 | 바이트 동일 `123aee4acc16eb48…` |
| **NIA 14-026 루브릭 정의 (dataset verbatim)**: | 0건 | 바이트 동일 `d4eb27f6cfdf0b84…` |
| **매핑 근거**: | 0건 | 바이트 동일 `c7103f349eec4657…` |
| **대리 범위 (proxy coverage)**: | 1건 | 치환으로 해시 상이(예상) |
| ### 3.2 `1B` content — 내용 | 0건 | 바이트 동일 `cde1ad12952d45e6…` |
| **NIA 14-026 루브릭 정의 (dataset verbatim)**: | 0건 | 바이트 동일 `3519e6bbfecd611c…` |
| **매핑 근거**: | 0건 | 바이트 동일 `3da3a0f3521c7ed9…` |
| **대리 범위 (proxy coverage)**: | 2건 | 치환으로 해시 상이(예상) |
| ### 3.3 `1C` organization — 조직 | 0건 | 바이트 동일 `9bdbc53f947e8e27…` |
| **NIA 14-026 루브릭 정의 (dataset verbatim)**: | 0건 | 바이트 동일 `930df239c66bff43…` |
| **매핑 근거**: | 0건 | 바이트 동일 `20d861c56cb43668…` |
| **대리 범위 (proxy coverage)**: | 1건 | 치환으로 해시 상이(예상) |
| ### 3.4 `1D` expression — 표현 (어법·어휘) | 0건 | 바이트 동일 `b545aa4f380c6bda…` |
| **NIA 14-026 루브릭 정의 (dataset verbatim)**: | 0건 | 바이트 동일 `77f1734b19bef58c…` |
| **매핑 근거**: | 0건 | 바이트 동일 `816b97bc325a3004…` |
| **대리 범위 (proxy coverage)**: | 0건 | 바이트 동일 `ab4e210208572de6…` |
| ## 4. Stage 5에서의 사용 | 0건 | 바이트 동일 `3d954c00a0b6a7a3…` |
| ## 5. 매핑의 한계 (v2.3 §7.6 해석 식별성) | 0건 | 바이트 동일 `a5d04e80edff029a…` |
| ### 5.1 구인 부분 대리 (proxy coverage) | 1건 | 치환으로 해시 상이(예상) |
| ### 5.2 학년 발달 단계 misinterpretation | 1건 | 치환으로 해시 상이(예상) |
| ### 5.3 대안 매핑 — robustness 분석 범위 | 1건 | 치환으로 해시 상이(예상) |
| ## 6. 보호 절차 (internal consensus scope) | 1건 | 치환으로 해시 상이(예상) |
| ## 7. 버전 이력 | 5건 | 치환으로 해시 상이(예상) |

## main_contrast_preregistered_v1.3.md

신원 정보 없음 — **원본 바이트 동일 공개**. 공개본 SHA-256 = 사전 명세 앵커 SHA:
`c6c58acdee918addbf57288adbf15b35fe19b2db10f9d61ee708b8f253526804`

