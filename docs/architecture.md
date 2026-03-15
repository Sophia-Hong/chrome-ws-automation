# Architecture: Chrome WebSocket Browser Automation

## Design Decisions

### Why WebSocket + Extension (not Playwright/Selenium)?

| | Playwright/Selenium | WebSocket + Extension |
|---|---|---|
| 브라우저 | 별도 인스턴스 필요 | 기존 Chrome 사용 |
| 로그인 | 매번 다시 로그인 | 세션 유지 |
| 안정성 | 브라우저 크래시 가능 | Extension은 안정적 |
| 감지 | 자동화 감지됨 | 일반 사용자와 동일 |
| 리소스 | 메모리 많이 사용 | 가벼움 |

### keke_appa 방식 분석

keke_appa의 30일 레딧 마케팅 에이전트 핵심:
1. **Chrome Extension이 브라우저 제어** — Puppeteer/Playwright 대신
2. **WebSocket으로 양방향 통신** — HTTP polling보다 빠르고 안정적
3. **Python 서버가 로직 담당** — Extension은 순수 실행기
4. **스냅샷 기반 상태 파악** — DOM 전체를 파싱하지 않고 필요한 정보만

### 우리 구현의 차이점
- **Manifest V3** 사용 (V2는 deprecated)
- **Service Worker** 기반 background (persistent background page 없음)
- **재연결 로직** 내장 (서버 재시작 시 자동 복구)
- **스냅샷 구조화** — links, inputs, buttons 분리 반환

## Data Flow

```
1. User/Agent → Python CLI/API
2. Python → WebSocket → Extension background.js
3. background.js → chrome.tabs.sendMessage → content.js
4. content.js → DOM 조작/읽기
5. content.js → background.js → WebSocket → Python
6. Python → 결과 반환
```

## Security Notes
- WebSocket은 localhost only (외부 접근 불가)
- content script는 페이지 컨텍스트와 격리됨
- evaluate는 content script 컨텍스트에서 실행 (제한적)
