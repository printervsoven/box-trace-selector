# KL / Codex 인수인계 묶음

생성일: 2026-08-08

이 묶음은 현재 대화에서 진행한 **mixed tensor–spinor box operator와 n=2 trace / R^2 상쇄 검토**를 Codex에서 이어가기 위한 자료입니다.

> 코드 전용 Git 저장소에서는 개인정보와 원문 저작물을 보호하기 위해
> `conversation/`, `attachments/`, 생성 PDF/CSV를 제외합니다. 아래 문서 목록은
> 원래 로컬 인수인계 묶음의 출처 기록이며, 계산 코드와 테스트 실행에는 필요하지 않습니다.

## 1. 먼저 볼 파일

1. `conversation/KL_conversation_transcript.pdf`
   - 사용자와 어시스턴트에게 화면에 표시된 현재 대화 전체를 PDF로 정리한 103쪽 문서입니다.
   - 시스템·개발자 지시, 숨은 추론, 내부 도구 로그는 포함하지 않습니다.
2. `conversation/KL_conversation_transcript.md`
   - 검색·복사·수정에 편리한 동일 대화의 Markdown 원문입니다.
3. `attachments/main(3).pdf`
   - mixed tensor–spinor로 확장된 box operator의 주 자료입니다.
4. `attachments/2506.21143v2.pdf`
   - Universal Box Operator 논문입니다.
5. `attachments/bifundamental_n2_full_trace(2).pdf`
   - bifundamental spinor의 exact formal n=2 trace 정리입니다.
6. `attachments/bifundamental_n1_trace(2).pdf`
   - bifundamental spinor의 n=1 trace 정리입니다.

## 2. 직접 검산 코드

계산 엔진과 브라우저 UI:

```text
generated/direct_box2_verification/verify_direct_box2.py
generated/direct_box2_verification/trace_selector_web.py
```

LaTeX 브라우저 선택 화면 실행:

```bash
python generated/direct_box2_verification/trace_selector_web.py
```

Windows에서 `python` 명령이 설정되지 않은 경우에는 아래 실행 파일을 더블클릭하거나
터미널에서 실행할 수 있습니다. 시스템 Python과 Codex 내장 Python을 순서대로 자동 탐색합니다.

```text
generated/direct_box2_verification/run_trace_selector.cmd
```

실행하면 로컬 브라우저에서 8개 필드의 기호와 표현이 처음부터 MathJax LaTeX로 렌더링됩니다.
필드를 클릭한 다음 `n=1: tr(Box)` 또는 `n=2: tr(Box o Box)`를 고르면 `main(3).pdf`의
식 (2.1)–(2.6), (3.14)–(3.17), (E.9)–(E.11)에 쓰인 노테이션만 결과 화면에 표시됩니다.
`n=1`은 spinor trace를 완전히 평가한 식을 보여줍니다. `T, n=2`는 식 (B.9)–(B.10)의 Clifford
convention과 (E.9)–(E.11)의 endomorphism을 현재 D=10 Majorana-Weyl, dim 16 specialization에
적용해 329개 pre-Clifford candidate를 local-Lorentz metric pairing까지 전개한 뒤, 모든 metric을
배경 텐서의 위·아래 Lorentz 지표에 흡수합니다. factor 내부 보통 편미분의 교환성을 적용해 정렬한
full factor AST와 외부 미분 tuple이 같은 항만 합친 최종 Einstein 수축식은 404개 항입니다. `phi, n=2`는
scalar specialization을 먼저 적용해 모든
covariant `D`를 제거하고, 곱의 미분법까지 전개한 14개 ordinary-partial 항을 보여줍니다.
나머지 raw tensor 필드의 `n=2`도 식 (2.3)-(2.5)로 single-Box endomorphism을 먼저
특수화합니다. 동일-sector symmetric connection contraction의 label-action 소거를 반영한 뒤
두 Box를 ordinary-compose하여 모든 covariant `D`를 제거하고, total generator를 실제 spinor
slot에 배분합니다. 길이 2, 3, 4 bivector의 bare trace는 식 (B.9)–(B.10)의 normalization으로
2, 8, 60개 raw metric pairing을 먼저 완전 분배합니다. 이 bare trace identity 자체를 줄이지는
않습니다. 각 generator label이 coefficient AST의 정확히 한 antisymmetric background-pair slot에
나타나는지 검사한 whole coefficient-times-trace monomial에서만 background 부호를 포함한
dummy-pair flip을 canonicalize합니다. 각 metric edge는 한 endpoint를 아래 지표, 다른 endpoint를
위 지표로 바꾸며 pair 내부 endpoint 순서를 보존하므로 추가 antisymmetry 부호가 생기지 않습니다.
각 dummy는 정확히 한 번 위에, 한 번 아래에 나타나는지 fail-closed로 검사합니다. mixed-index
curvature는 원래 antisymmetric two-form의 한 지표를 올린 성분이므로 서로 다른 높이를 bracket으로
묶지 않습니다. 최종 표시 행 수는 `B_LL/B_RR` 각각 192개,
`U_L/U_R` 각각 192개, `U_LLR/U_LRR` 각각 404개입니다. slot-signature별 감사 provenance는
`B_LL/B_RR` 각각 222개, `U_L/U_R` 각각 195개, `U_LLR/U_LRR` 각각 446개로 별도 유지합니다.
우측작용 순서, `G=gamma/2`, `barred G=-barred gamma/2`, 빈 slot의 spinor 차원 16은 최종
coefficient에 포함됩니다. 표준 `n=2` 수식에는 covariant `D`, total generator, gamma matrix,
explicit local metric이 남지 않습니다. 서로 다른 ordered block도 factor 내부 보통 편미분을
commute-sort한 full absorbed factor AST와 외부 미분 tuple이 같은 경우에는 합치지만, 그 밖의
tensor identity나 contraction-graph orientation
동치는 적용하지 않습니다.
전개 범위는 `D=10`, `dim S=dim barred S=16`, density weight 0이며 irreducible projection을
적용하지 않은 raw tensor product입니다.
내부 검산용 `I/J`, `t2/t3/t4`, moment-basis 표기는 표준 브라우저 화면에 노출하지 않습니다.

아래 TeX/PDF/CSV는 기존 계산 엔진의 내부 검산 산출물입니다. paper-native 표준 화면과 구분해
CLI에서 생성하며, 브라우저 결과 링크에는 노출하지 않습니다.

기존 터미널 선택 화면은 직접 계산 엔진을 실행하면 계속 사용할 수 있습니다.

```bash
python generated/direct_box2_verification/verify_direct_box2.py
```

- `trace_<FIELD>_n<N>.tex`: LaTeX 원문
- `trace_<FIELD>_n<N>.pdf`: XeLaTeX로 렌더링한 결과와 0이 아닌 primitive 기여식
- `trace_<FIELD>_n<N>_details.csv`: 항별 coefficient와 trace moment
- `trace_<FIELD>_n<N>_expanded.csv`: 선택 moment까지 곱한 primitive 기여
- `trace_<FIELD>_n<N>_summary.json`: 선택 결과 요약

자동 실행 예:

```bash
python generated/direct_box2_verification/verify_direct_box2.py --field T --trace-order 1
python generated/direct_box2_verification/verify_direct_box2.py --field ULLR --trace-order 2 --no-open
```

기존 전체 `n=2` coefficientwise 검산은 다음처럼 실행합니다.

```bash
python generated/direct_box2_verification/verify_direct_box2.py --verify-all
```

Python 코드는 외부 패키지를 사용하지 않습니다. 브라우저 수식 렌더링에는 MathJax CDN 연결이,
PDF 렌더링에는 `xelatex`가 필요합니다.
전체 검산이 정상 실행되면 JSON 요약의 `status`가 `PASS`이고 다음 가중합이 모두 0으로 출력됩니다.

주의: 필드 표의 상대 가중치는 `n=2` 상쇄용입니다. 선택 결과의 boxed 식은 단일 필드의
가중치 없는 유한차원 trace이며, `n=1` 결과에는 이 `n=2` 가중치를 적용하지 않습니다.
또한 선택 결과는 determinant prefactor와 좌표 functional trace를 포함한 전체 one-loop
유효작용이 아니라 그 안에 들어가는 representation trace입니다.

```text
D = L = R = LL = RR = LR = 0
```

코드의 검증 범위는 다음과 같습니다.

```text
raw tensor products, weight zero,
common universal box/background/section/measure/regulator,
finite-dimensional spinor supertrace coefficientwise before momentum integration
```

즉, 이 계산은 다음 raw tensor-product 후보에 대한 symbolic coefficientwise 검산입니다.

```text
T, phi, B_LL, B_RR, U_L, U_R, U_LLR, U_LRR
```

대칭화·반대칭화·gamma-traceless projection, 실제 Type II mass level, GSO projection, Majorana/Pfaffian 정규화, gauge constraints 및 ghosts까지 자동으로 증명하는 코드는 아닙니다. 물리적 스펙트럼으로 해석하려면 이 조건들을 별도로 넣어야 합니다.

## 3. 코드 실행 시 생성되는 주요 파일

- `verification_summary.json`: 전체 실행 요약
- `verification_report.txt`: 사람이 읽기 쉬운 요약
- `field_moments.csv`: 각 필드의 `(D,L,R,LL,RR,LR)` 계수와 가중합
- `universal_box2_118_terms.csv`: exact composition의 118개 block term을 primitive background monomial로 전개한 ledger
- `box2_terms_by_field.csv`: 필드별 exact-term 대입 및 trace-basis 분해
- `coefficientwise_verification.csv`: exact term별 coefficientwise 검증
- `slot_expansion_by_field.csv`: 실제 tensor-product spinor slot별 전개
- `slot_coefficientwise_verification.csv`: slot-level 상쇄 검증
- `direct_box2_verification.pdf`: 앞선 검산 보고서

## 4. 폴더 구조

```text
KL_codex_handoff/
├── README_Codex.md
├── SHA256SUMS.txt
├── conversation/
│   ├── KL_conversation_transcript.pdf
│   ├── KL_conversation_transcript.md
│   └── assets/
├── attachments/
│   ├── main(3).pdf
│   ├── 2506.21143v2.pdf
│   ├── bifundamental_n2_full_trace(2).pdf
│   ├── bifundamental_n1_trace(2).pdf
│   └── 대화에 첨부된 PNG 이미지 2개
└── generated/
    ├── direct_box2_verification/
    └── archive/direct_box2_verification_bundle.zip
```

## 5. Codex에서 이어갈 때 권장 순서

1. `conversation/KL_conversation_transcript.md`에서 가장 마지막 계산과 표기법을 확인합니다.
2. `main(3).pdf`의 일반 total-generator box 정의와 ordered sequential action 규약을 기준으로 삼습니다.
3. `verify_direct_box2.py`를 실행하여 현재 symbolic check를 재현합니다.
4. 다음 단계에서는 raw tensor product라는 가정을 제거하고, 필요한 irreducible projection과 실제 fermionic quadratic action을 명시합니다.
5. 실제 Type II 상쇄를 주장하려면 질량, multiplicity, chirality/reality, Pfaffian, gauge fixing, ghost 및 동일 regulator를 포함하여 다시 계산합니다.

`SHA256SUMS.txt`는 ZIP 내부 파일의 무결성 확인용입니다.
