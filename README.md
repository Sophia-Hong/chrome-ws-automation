# Chrome WebSocket Browser Automation Engine

**keke_appa 방식** — Chrome Extension + WebSocket + Python으로 기존 Chrome 브라우저를 자동화.

## 왜 이 방식?

| | Playwright/Puppeteer | 이 방식 (keke_appa) |
|---|---|---|
| 브라우저 | 별도 인스턴스 실행 | **기존 Chrome 사용** |
| 로그인 세션 | 매번 새로 | **유지됨** |
| 리소스 | 무거움 | **가벼움** |
| 감지 회피 | 봇 탐지에 걸림 | **일반 사용자처럼 보임** |
| 설치 | npm + 브라우저 다운로드 | **Extension 하나** |

## 아키텍처

```
┌─────────────────┐     WebSocket      ┌──────────────────┐
│ Chrome Extension │ ◄──────────────── │  Python Server   │
│  (content.js)   │  ws://localhost:9876│  (bridge.py)     │
│  DOM 조작/스냅샷  │ ────────────────► │  명령 전송/결과 수신 │
└─────────────────┘                    └──────────────────┘
                                              ▲
                                              │
                                       ┌──────────────┐
                                       │ client.py    │
                                       │ CLI / Script │
                                       └──────────────┘
```

## 빠른 시작

### 1. Python 서버 실행

```bash
cd server
pip install -r requirements.txt
python bridge.py
```

### 2. Chrome Extension 설치

1. Chrome → `chrome://extensions`
2. "개발자 모드" ON
3. "압축 해제된 확장 프로그램 로드" → `extension/` 폴더 선택
4. Extension이 자동으로 `ws://localhost:9876`에 연결

### 3. 명령 실행

**REPL 모드 (bridge.py 실행 중):**
```
bridge> navigate https://reddit.com/r/tenants
bridge> snapshot
bridge> getText h1
bridge> getLinks reddit
bridge> click .search-input
bridge> fill .search-input "security deposit California"
```

**스크립트 모드:**
```bash
python client.py navigate "https://reddit.com/r/tenants"
python client.py snapshot
python client.py getText "h1"
python client.py getLinks "deposit"
```

## 지원 명령어

| Command | Params | Description |
|---------|--------|-------------|
| `navigate` | `{url}` | 페이지 이동 |
| `click` | `{selector}` | 요소 클릭 |
| `fill` | `{selector, value}` | 입력 필드 채우기 |
| `getText` | `{selector?}` | 텍스트 추출 (없으면 전체) |
| `getLinks` | `{filter?}` | 링크 목록 (필터 가능) |
| `evaluate` | `{expression}` | JS 실행 |
| `snapshot` | `{}` | 페이지 스냅샷 (제목/헤딩/폼/메타/텍스트) |
| `querySelector` | `{selector}` | 요소 검색 |
| `scroll` | `{selector?/y?}` | 스크롤 |
| `waitForSelector` | `{selector, timeout?}` | 요소 대기 |
| `getTabs` | `{}` | 열린 탭 목록 |
| `setActiveTab` | `{tabId}` | 활성 탭 변경 |

## 활용 예시

### 레딧 페인포인트 수집
```python
import asyncio
from client import send_command

async def scrape_reddit():
    await send_command("navigate", {"url": "https://reddit.com/r/tenants"})
    await asyncio.sleep(2)
    links = await send_command("getLinks", {"filter": "security deposit"})
    for link in links.get("result", {}).get("links", []):
        print(link["text"], link["href"])

asyncio.run(scrape_reddit())
```

## 테스트

```bash
cd tests
pip install pytest pytest-asyncio
pytest test_bridge.py -v
```

## 프로젝트 구조

```
chrome-ws-automation/
├── extension/
│   ├── manifest.json      # Manifest V3
│   ├── background.js      # WebSocket 연결 관리
│   └── content.js         # DOM 명령 실행
├── server/
│   ├── bridge.py          # WebSocket 서버 + REPL
│   ├── client.py          # CLI 클라이언트
│   └── requirements.txt
├── tests/
│   └── test_bridge.py
└── README.md
```

## Phase 3 (예정)

- OpenClaw exec 연동
- 레딧 수집 파이프라인 (서브레딧 모니터링 → 페인포인트 추출)
- 콘텐츠 파이프라인 (비디오 스크립트, 댓글 드래프트)
