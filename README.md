# Chrome WebSocket Browser Automation Engine

**keke_appa 방식** — Chrome Extension + WebSocket + Python으로 기존 Chrome 브라우저를 자동화.

## 왜 이 방식?

| | Playwright/Puppeteer | 이 방식 (keke_appa) |
|---|---|---|
| 브라우저 | 별도 인스턴스 필요 | 기존 Chrome 사용 |
| 로그인 | 매번 다시 로그인 | 세션 유지 |
| 안정성 | 브라우저 크래시 가능 | Extension은 안정적 |
| 감지 | 자동화 감지됨 | 일반 사용자와 동일 |
| 리소스 | 메모리 많이 사용 | 가벼움 |

## 아키텍처

```
Chrome Extension (content script + service worker)
    ↕ WebSocket (ws://localhost:9876)
Python Server (asyncio + websockets)
    → navigate, click, fill, evaluate, snapshot 등 명령
    ← DOM 결과 + 스냅샷 반환
        → Pipelines (Reddit scraper, content pipeline)
```

## 빠른 시작

### 1. Chrome Extension 설치
1. `chrome://extensions` 접속
2. "개발자 모드" 활성화
3. "압축해제된 확장 프로그램을 로드합니다" → `extension/` 폴더 선택
4. 확장 아이콘에 "ON" 뱃지 확인

### 2. Python 서버 실행
```bash
cd server
pip install -r requirements.txt

# Option A: 대화형 CLI (서버 + REPL)
python server.py --cli

# Option B: 서버만 실행 (API 연동용)
python server.py

# Option C: Bridge 모드 (다중 클라이언트 지원)
python bridge.py
```

### 3. 명령 실행

**대화형 CLI:**
```
>>> navigate https://reddit.com/r/landlord
>>> snapshot
>>> getText .Post
>>> click "button[data-click-id=body]"
>>> evaluate "document.title"
>>> getLinks
>>> getTabs
```

**One-shot CLI:**
```bash
python cli.py navigate https://reddit.com
python cli.py snapshot
python cli.py evaluate "document.title"
python cli.py getText ".main-content"
```

**Programmatic client:**
```bash
python client.py navigate "https://reddit.com/r/tenants"
python client.py snapshot
```

## 지원 명령어

| 명령 | 설명 | 파라미터 |
|------|------|----------|
| `navigate` | URL로 이동 | `url` |
| `click` | 요소 클릭 | `selector` 또는 `text` |
| `fill` | 입력필드 채우기 | `selector`, `value` |
| `evaluate` | JS 표현식 실행 | `expression` |
| `snapshot` | 페이지 스냅샷 (links, inputs, buttons) | - |
| `getText` | 텍스트 추출 | `selector` (선택) |
| `getLinks` | 모든 링크 추출 | - |
| `getTitle` | 현재 페이지 제목 | - |
| `getTabs` | 열린 탭 목록 | - |
| `ping` | 연결 확인 | - |

## 파이프라인 (Phase 3)

### Reddit Pain Point Scraper
```bash
python -m pipelines.reddit_scraper \
  --subreddit tenants \
  --keywords "security deposit,landlord,lease" \
  --max-posts 20 \
  --output results.json
```

### Content Pipeline
```bash
# Reddit 답변 드래프트 생성
python -m pipelines.content_pipeline --input results.json --type comment-drafts

# 숏폼 비디오 스크립트 아웃라인
python -m pipelines.content_pipeline --input results.json --type video-scripts
```

## 프로젝트 구조

```
chrome-ws-automation/
├── extension/           # Chrome Extension (Manifest V3)
│   ├── manifest.json
│   ├── background.js    # Service Worker — WebSocket 연결 관리
│   └── content.js       # Content Script — DOM 조작
├── server/              # Python WebSocket Server
│   ├── server.py        # 메인 서버 + 대화형 CLI
│   ├── bridge.py        # 다중 클라이언트 브릿지 서버
│   ├── client.py        # 프로그래밍 클라이언트
│   ├── cli.py           # One-shot CLI
│   ├── test_server.py   # 서버 테스트
│   └── requirements.txt
├── pipelines/           # 자동화 파이프라인
│   ├── reddit_scraper.py
│   └── content_pipeline.py
├── tests/
│   └── test_bridge.py
├── docs/
│   └── architecture.md
└── README.md
```

## 테스트
```bash
cd server && python test_server.py
cd tests && python -m pytest test_bridge.py -v
```

## 보안
- WebSocket은 **localhost only** (외부 접근 불가)
- Content script는 페이지 컨텍스트와 격리
- `evaluate`는 content script 컨텍스트에서 실행

## 참조
- [Backlog Issue #51](https://github.com/Sophia-Hong/backlog/issues/51)
