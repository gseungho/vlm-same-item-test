# 브랜드 이름은 VLM의 "같은 상품" 판정을 바꾸는가

VLM(이미지와 글을 함께 읽는 언어 모델)인 Claude Haiku 5.5, Sonnet 5.5, Opus 5.5에게 상품 사진 두 장을 보여 주고 같은 상품인지 물은 실험의 기록이다. 사진은 ABO(Amazon Berkeley Objects, 아마존의 실제 상품 목록과 사진을 공개한 자료)에서 가져왔다. 사진은 그대로 두고 각 사진에 붙는 브랜드 이름 한 줄만 바꿔, 그것만으로 판정이 달라지는지 측정했다. 출발점은 같은 공장에서 만든 물건을 브랜드만 달리 파는 일과 택갈이(남의 상품에 라벨만 바꿔 다는 일)다.

설계, 판정 규칙, 결과, 해석은 모두 한국어로 썼다. 처음 읽는다면 `docs/EVIDENCE.md`의 "읽는 법"부터 보면 된다.

## 무엇이 나왔는가

확인 실험(E-006): 새 패션 앵커(실험의 기준이 되는 상품) 73개로 파일럿의 주장 11개를 판정했고 모두 확인됐다. 구간은 Bonferroni로 보정한 99.55% 구간이다.

- 같은 물건의 사진이어도 서로 다른 무명 브랜드 이름을 붙이고 "같은 상품인가"(Q1)로 물으면 "같다"가 줄었다. 줄어든 폭은 Haiku +72.6%p, Sonnet +27.4%p, Opus +56.2%p다.
- Sonnet과 Opus는 "브랜드 이름을 빼면 같은 물건인가"(Q2)로 묻거나 이름을 판매자 줄로 붙이면 이 효과가 절반 넘게 사라졌다. Sonnet은 완전히 사라졌다.
- Haiku는 Q2에서도 효과가 남았고, 남은 효과는 "다르다"보다 "알 수 없다"로 갔다.
- Q1에서 Opus의 효과가 Sonnet보다 컸다(+28.8%p).

탐색(확인된 결과로 쓰지 않음): 파일럿(E-001~E-005)과 가구, 조명(E-007, E-008)이다. 가구에서도 Q2로 물으면 Sonnet과 Opus의 효과가 사라졌다. 유명 브랜드 이름의 효과는 모델과 상품군에 따라 방향이 바뀌었다.

이 결과는 흰 배경의 카탈로그 사진, 신발과 가방(확인 실험), 한 상품 목록의 두 사진에 대한 것이다.

## 순서 기록

확인 실험의 설계서 `docs/specs/2026-11-04-same-item-confirm.md`는 모델을 부르기 전에 이 저장소의 첫 커밋 `b49d880`(2026-11-04 14:21, 한국 시간)으로 올렸다. 판정 규칙과 구간을 결과보다 먼저 정했다는 기록이다. 나머지 파일은 결과를 정리한 뒤 함께 올렸다. 설계서 맨 위의 공개본 안내에 "링크가 열리지 않는다"고 적었지만, 이제 그 링크가 가리키는 파일 대부분이 이 저장소에 있다.

## 무엇이 있는가

| 경로 | 내용 |
| --- | --- |
| `docs/specs/` | 설계서. 파일럿(`2026-11-02-same-item-pilot.md`)과 확인 실험(`2026-11-04-same-item-confirm.md`) |
| `docs/EVIDENCE.md` | 결과와 해석(E-001~E-008). 비공개 연구 기록에서 그대로 옮겼다 |
| `docs/literature/RELATED_WORK.md` | 선행연구와 데이터를 확인한 기록 |
| `configs/` | 앵커, 사진 해시, 조건, 보기 순서를 고정한 설정. 파일럿 `same_item_v1.json`, 확인 `same_item_v2_fashion.json`, `same_item_v2_furniture.json` |
| `results/` | 모델의 답(`*.jsonl`, 받은 메시지 그대로), 표(`report.md`), 실행 기록(`manifest.json`: 코드 revision, 설정 해시, seed, 모델 이름). `smoke/`와 `main/`은 파일럿, `confirm_*`는 확인 실험 |
| `src/vtrust/`, `tests/` | 요청을 만들고 보내고 분석하는 코드와 테스트 |
| `tools/` | ABO에서 후보 사진을 모으고 고르는 도구. 모델 API를 부르지 않는다 |
| `prompts/agent_prompts.md` | 후보 쌍을 고르고 1000픽셀 사진으로 다시 확인한 에이전트(Claude Fable 5.1, 실험 대상 아님)에게 준 지시 |

같은 코드 묶음(`vtrust`)에 다음 실험인 기사와 사진의 불일치 실험 코드도 들어 있다. 그 실험의 기록은 https://github.com/gseungho/vlm-caption-test 에 있다.

## 다시 계산하기

표는 저장된 답에서 다시 만들 수 있다. API를 부르지 않는다.

```
python -m venv .venv
.venv/bin/pip install -e ".[dev,sample]"   # Windows는 .venv\Scripts\pip. sample은 테스트가 쓰는 Pillow
.venv/bin/python -m pytest
.venv/bin/python -m vtrust.run report main                                          # 파일럿
.venv/bin/python -m vtrust.run report main --config configs/same_item_v2_fashion.json
.venv/bin/python -m vtrust.run report main --config configs/same_item_v2_furniture.json
```

모델에게 다시 물으려면(유료) 사진이 `data/pairs/photos/<ABO 이미지 ID>.jpg`에 있어야 한다. 코드는 사진의 SHA-256이 설정에 적힌 값과 같을 때만 보낸다. 사진은 ABO 원본의 긴 변이 1000픽셀을 넘으면 1000픽셀로 줄인 것이라 이미지 라이브러리 버전이 다르면 해시가 달라질 수 있다. API 키는 환경 변수 `KSYCO_ANTHROPIC_API_KEY`에서 읽는다. 모델이 바뀌었을 수 있으므로 같은 답이 나온다는 보장은 없다.

## 함께 밝힐 점

- 각 조건을 한 번씩만 물었다. 같은 질문에 매번 다르게 답하는 흔들림은 따로 떼어 보지 못했다.
- 세 모델 모두 adaptive thinking(생각할지와 얼마나 생각할지를 모델이 정하는 설정)과 생각 요약을 켰다. Sonnet은 거의 생각하지 않고 답했다.
- 연구 진행 기록(작업 일지, 현재 상태, 결정 기록)은 비공개로 두었다. `docs/EVIDENCE.md`에 나오는 `RESEARCH_PLAN.md`, `LOG.md`가 그것이다.

## 라이선스

- 코드(`src/`, `tests/`, `tools/`): MIT. `LICENSE`를 보라.
- 문서, 설정, 결과(`docs/`, `configs/`, `results/`, `prompts/`, 이 README): CC BY 4.0(https://creativecommons.org/licenses/by/4.0/).
- ABO 데이터와 사진: Amazon, CC BY 4.0(https://amazon-berkeley-objects.s3.amazonaws.com/index.html). 사진 파일은 이 저장소에 없고 설정에 이미지 ID만 있다.
