# 브랜드 이름은 VLM의 "같은 상품" 판정을 바꾸는가

VLM은 이미지와 글을 함께 읽는 언어 모델이다. 이 저장소는 Claude Haiku 5.5, Sonnet 5.5, Opus 5.5로 한 실험의 기록이다. 모델에게 상품 사진 두 장을 보여 주고 같은 상품인지 물었다. 사진은 ABO(Amazon Berkeley Objects, 아마존이 실제 상품 목록과 사진을 공개한 자료)에서 가져왔다. 사진은 그대로 두고 각 사진에 붙는 브랜드 이름 한 줄만 바꿔서, 그것만으로 판정이 달라지는지 측정했다. 출발점은 같은 공장에서 만든 물건을 브랜드만 달리 파는 일과 택갈이(남의 상품에 라벨만 바꿔 다는 일)다.

설계, 판정 규칙, 결과, 해석은 모두 한국어로 썼다. 처음 읽는다면 `docs/EVIDENCE.md`의 "읽는 법"부터 보면 된다.

## 주요 결과

확인 실험(E-006): 신발과 가방에서 새로 고른 기준 상품(앵커) 73개로 파일럿에서 나온 주장 네 개를 다시 판정했다. 판정 항목은 11개였고 모두 "확인"으로 나왔다. 여러 항목을 함께 판정하면 그중 하나가 우연히 확인될 확률이 커진다. 그래서 Bonferroni 보정으로 넓힌 99.55% 구간을 썼다. 아래에서 %p(퍼센트포인트)는 두 백분율의 차이다.

- 같은 물건의 사진 두 장에 서로 다른 무명 브랜드 이름을 붙이고 "같은 상품인가"(Q1)로 물었다. 이름이 없을 때보다 "같다"고 답한 비율이 Haiku는 72.6%p, Sonnet은 27.4%p, Opus는 56.2%p 줄었다.
- Sonnet과 Opus는 "브랜드 이름을 빼면 같은 물건인가"(Q2)로 묻거나, 이름을 `Brand:` 대신 `Seller:`(판매자) 줄로 붙이면 이 감소가 절반 넘게 사라졌다. 이번 표본에서 Sonnet은 감소가 전혀 없었다.
- Haiku는 Q2로 물어도 "같다"고 답한 비율이 줄었다. 이때 늘어난 답은 "다르다"보다 "알 수 없다"가 많았다.
- Q1에서 Opus의 감소 폭이 Sonnet보다 28.8%p 컸다.

탐색(확인된 결과로 쓰지 않음): 파일럿(E-001부터 E-005)과 가구, 조명(E-007, E-008)이다. 가구에서도 Q2로 물으면 Sonnet과 Opus의 감소가 사라졌다. 유명 브랜드 이름(패션은 Gucci, Prada, Coach, 가구는 IKEA, West Elm, Pottery Barn)을 붙였을 때의 효과는 모델과 상품군에 따라 방향이 바뀌었다.

확인 실험의 결과는 흰 배경의 카탈로그 사진, 신발과 가방, 한 상품 목록에서 가져온 두 사진으로 얻은 것이다.

## 설계서를 먼저 공개한 기록

확인 실험의 설계서 `docs/specs/2026-11-04-same-item-confirm.md`는 모델을 부르기 전에 이 저장소의 첫 커밋 `b49d880`(2026-11-04 14:21, 한국 시간)으로 올렸다. 판정 규칙과 구간을 결과보다 먼저 정했다는 기록이다. 나머지 파일은 결과를 정리한 뒤 함께 올렸다. 설계서 맨 위의 안내는 설계서만 먼저 올렸을 때 쓴 것이어서, 그 아래에 날짜를 붙인 한 줄을 더했다.

## 저장소 구성

| 경로 | 내용 |
| --- | --- |
| `docs/specs/` | 설계서. 파일럿(`2026-11-02-same-item-pilot.md`)과 확인 실험(`2026-11-04-same-item-confirm.md`) |
| `docs/EVIDENCE.md` | 결과와 해석(E-001부터 E-008). 비공개 연구 기록에서 옮겼다 |
| `docs/literature/RELATED_WORK.md` | 선행연구와 데이터를 확인한 기록 |
| `configs/` | 앵커, 사진 해시, 조건, 보기 순서를 고정한 설정. 파일럿은 `same_item_v1.json`, 확인 실험은 `same_item_v2_fashion.json`과 `same_item_v2_furniture.json` |
| `results/` | 모델의 답(`*.jsonl`, 받은 메시지 그대로), 결과 표(`report.md`), 실행 기록(`manifest.json`: 코드 revision, 설정 해시, seed, 모델 이름). `smoke/`와 `main/`은 파일럿, `confirm_*`는 확인 실험 |
| `src/vtrust/`, `tests/` | 요청을 만들고 보내고 분석하는 코드와 테스트 |
| `tools/` | ABO에서 후보 사진을 모으고 고르는 도구. 모델 API를 부르지 않는다 |
| `prompts/agent_prompts.md` | 후보 쌍을 고르고 1000픽셀 사진으로 다시 확인한 에이전트(Claude Fable 5.1, 실험 대상 아님)에게 준 지시 |

같은 코드 묶음(`vtrust`)에 다음 실험인 기사와 사진의 불일치 실험 코드도 들어 있다. 그 실험의 기록은 https://github.com/gseungho/vlm-caption-test 에 있다.

## 결과 표 다시 만들기

저장된 답으로 결과 표(`report.md`)를 다시 만들 수 있다. API를 부르지 않는다.

```
python -m venv .venv
.venv/bin/pip install -e ".[dev,sample]"   # Windows는 .venv\Scripts\pip. sample은 테스트가 쓰는 Pillow
.venv/bin/python -m pytest
.venv/bin/python -m vtrust.run report main                                          # 파일럿
.venv/bin/python -m vtrust.run report main --config configs/same_item_v2_fashion.json
.venv/bin/python -m vtrust.run report main --config configs/same_item_v2_furniture.json
```

모델에게 다시 물으려면(유료) 사진이 `data/pairs/photos/<ABO 이미지 ID>.jpg`에 있어야 한다. 코드는 사진의 SHA-256이 설정에 적힌 값과 같을 때만 보낸다. 사진은 ABO 원본의 긴 변이 1000픽셀을 넘으면 1000픽셀로 줄인 것이다. 그래서 이미지 라이브러리 버전이 다르면 해시가 달라질 수 있다. API 키는 환경 변수 `KSYCO_ANTHROPIC_API_KEY`에서 읽는다. 모델이 바뀌었을 수 있으므로 같은 답이 나온다는 보장은 없다.

## 공개하지 않은 자료

- ABO 사진 파일. 설정에는 이미지 ID만 있다.
- 연구 진행 기록(작업 일지, 현재 상태, 결정 기록, 교차 검토 기록). `docs/EVIDENCE.md`와 설계서에 나오는 `RESEARCH_PLAN.md`, `LOG.md`, `STATUS.md`가 그것이고, 이 파일로 가는 링크는 열리지 않는다.

## 결과를 읽을 때 주의할 점

- 각 조건을 한 번씩만 물었다. 같은 질문을 다시 했을 때 답이 달라지는 정도는 따로 측정하지 않았다.
- 세 모델 모두 adaptive thinking(답하기 전에 생각할지와 얼마나 생각할지를 모델이 정하는 설정)을 켜고 생각 요약을 받았다. Sonnet은 생각을 한 번도 쓰지 않고 답했다.
- 실제 택갈이 상품을 판정한 실험이 아니다. 이 값을 실제 판매 플랫폼의 판별 정확도로 읽으면 안 된다.

## 라이선스

- 코드(`src/`, `tests/`, `tools/`): MIT. `LICENSE`를 보라.
- 문서, 설정, 결과(`docs/`, `configs/`, `results/`, `prompts/`, 이 README): CC BY 4.0(https://creativecommons.org/licenses/by/4.0/).
- ABO 데이터와 사진: Amazon, CC BY 4.0(https://amazon-berkeley-objects.s3.amazonaws.com/index.html). 사진 파일은 이 저장소에 없고 설정에 이미지 ID만 있다.
