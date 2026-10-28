# Codex로 사용하기

원본 게임 개발 스튜디오의 작업 지침을 유지하면서 Codex가 읽는 스킬과
역할 설정을 추가한 포크입니다. Claude Code 설치는 필요하지 않습니다.

## 시작

```sh
git clone https://github.com/JakeB-5/Claude-Code-Game-Studios.git my-game
cd my-game
python3 scripts/codex/studio.py check
codex
```

Codex 데스크톱 앱에서는 복제한 `my-game` 폴더를 프로젝트로 여세요.
프로젝트 스킬이 보이지 않으면 해당 폴더에서 새 세션을 시작하세요.
Python 3.11 이상, Bash, Git이 필요합니다. Windows에서는 Git Bash 또는
WSL 환경이 필요하며, 이 포크의 자동 검사는 macOS와 Linux를 대상으로 합니다.

첫 요청은 `$studio-start`입니다. 기존 게임 작업이 들어 있다면
`$studio-project-stage-detect`, 다음 단계가 궁금하면 `$studio-help`를 사용하세요.

| 할 일 | Codex 스킬 |
| --- | --- |
| 아이디어 구체화 | `$studio-brainstorm` |
| 게임 엔진 설정 | `$studio-setup-engine` |
| 설정 조회·변경 | `$studio-settings` |
| 작은 변경의 명세 작성 | `$studio-quick-design` |
| 구현 작업 나누기 | `$studio-create-stories` |
| 작업 구현 | `$studio-dev-story` |
| 코드 검토 | `$studio-code-review` |
| 완료 증거 확인 | `$studio-story-done` |

설정과 결과물은 게임 저장소 안에 유지됩니다. 이 스킬들은 공통 문서와
스크립트에 의존하므로 `SKILL.md` 파일만 전역 스킬 폴더로 복사하지 마세요.
사용자의 전역 Codex 설정이나 모델 설정은 설치 과정에서 변경하지 않습니다.

## 무엇이 변환됐나

- `.agents/skills/studio-*/SKILL.md`: 원본 74개 작업 흐름의 Codex 진입점.
- `.codex/agents/studio-*.toml`: 49개 역할. 모델과 권한은 현재 세션에서 상속.
- 루트와 각 주요 디렉터리의 `AGENTS.md`: Codex용 프로젝트 지침.
- `scripts/codex/studio.py`: 원본 설정 읽기, 참조 검사, 파일별 규칙 조회,
  기존 커밋·에셋·푸시 검사 연결.
- 원본 `.claude/`와 `CLAUDE.md`: 공통 지침으로 그대로 보존.

원본의 도구 이름, 인자, 상대경로, 사전 실행 구문은
[runtime.md](runtime.md)에 정의된 방식으로 해석합니다. 특히 Claude의
`!` 명령은 Codex에서 자동 실행되지 않아 `studio.py context NAME`이 실제
설정값을 읽어 전달합니다. `studio.py`는 셸 코드를 임의로 평가하지 않습니다.

자동 훅은 이식하지 않았습니다. 원본 검사 스크립트를 명시적으로 호출하며,
이것을 자동 차단이나 완전한 보안 통제로 설명하지 않습니다.

## 검증

계정이나 모델 호출 없이 실행하는 검사:

```sh
python3 scripts/codex/studio.py check
python3 -m unittest discover -s tests/codex -v
```

실제 Codex 실행 검사에는 로그인된 계정의 사용량이 소모됩니다. 원본 작업
폴더를 수정하지 않고 임시 복제본에서 실행하며, 결과와 로그 경로를 출력합니다.
모델 이름을 고정하지 않으며 CLI 기본 모델을 사용합니다. 사용자 config는
격리하지만 Codex가 제공하는 기본 스킬·정책과 인증은 그대로 적용됩니다.

```sh
python3 scripts/codex/live_test.py --case settings
python3 scripts/codex/live_test.py --case quick-design
python3 scripts/codex/live_test.py --case agent
python3 scripts/codex/live_test.py --case implementation
```

`agent`는 `studio-qa-tester` 역할의 하위 에이전트가 검토 보고서를 만드는지
확인합니다. 호스트 도구에 역할 선택 기능이 없으면 역할 파일을 직접 읽히는
대체 방식을 사용하고 이를 보고합니다. 네이티브 역할 자동 로딩을 통과했다고
간주하지 않습니다. 이 검사는 하위 에이전트가 부모 실행
기록을 읽을 수 있도록 로컬 Codex 세션 기록을 남깁니다. 나머지 검사는
임시 세션으로 실행합니다. `implementation`은 데이터 수정과 테스트
실행, 엔진 미설치 시 결과를 정직하게 보고하는지 확인합니다. 각 게임 엔진의
전체 제작 흐름과 시각 검증까지 보장하는 테스트는 아닙니다.

## 원본 업데이트

```sh
git remote add upstream https://github.com/Donchitos/Claude-Code-Game-Studios.git
git fetch upstream
git merge upstream/main
python3 scripts/codex/studio.py sync
python3 scripts/codex/studio.py check
python3 -m unittest discover -s tests/codex -v
```

`upstream`이 이미 있다면 remote 추가 단계는 생략하세요. 충돌은 변경 내용을
검토해 해결하세요. 스킬·역할 진입점은 생성 파일입니다. 생성 규칙을 바꾸려면
`scripts/codex/studio.py`를 수정한 뒤 `sync`하세요. 새 원본 사전 실행 구문이
지원되지 않으면 변환기는 실패를 보고하므로 해당 구문을 검토해 추가해야 합니다.

## 참고한 기존 변환판

- [chuanglibs](https://github.com/chuanglibs/Claude-Code-Game-Studios-Codex):
  원본 지침을 유지하고 Codex 진입점을 추가하는 접근.
- [Euraika-Labs](https://github.com/Euraika-Labs/Codex-Code-Game-Studios):
  Codex 스킬, 네이티브 역할, 검증 도구의 구분.
- [eiichimo](https://github.com/eiichimo/Codex-Game-Studios):
  원본 훅을 명시적인 검사 명령으로 연결하는 접근.

이 포크의 연결 도구와 테스트는 원본 v1.2.0을 기준으로 작성했습니다.
원본 제작자 Donchitos의 저작권 표시와 MIT 라이선스를 유지합니다.
