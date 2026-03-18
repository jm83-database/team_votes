# 팀 프로젝트 투표 시스템

온라인 교육 환경에서 프로젝트 발표 후 팀 간 투표를 진행할 수 있는 웹 애플리케이션입니다.
Azure Cosmos DB 연동 및 관리자 UI를 통한 과정/팀/학생 관리를 지원합니다.

## 주요 기능

### 관리자 기능
- **과정(코호트) 관리**: 교육과정 생성/삭제/활성화
- **학생 업로드**: students.json 파일 업로드로 학생 일괄 등록
- **드래그앤드롭 팀 빌더**: GUI에서 학생을 팀에 배치, 팀명/프로젝트명 편집
  - HTML5 Drag & Drop (데스크톱)
  - 드롭다운 이동 (모바일)
  - 균등 배분, 팀 수 조절
- **투표 제어**: 투표 시작/종료, 시간 설정, 투표 방식 (1개/3개 팀 선택)
- **실시간 결과 확인**: 팀별 순위, 학생별 투표 현황, CSV 다운로드

### 학생 기능
- 이름 + 비밀번호로 로그인 (활성 과정 자동 감지)
- 자신의 팀 제외한 팀에 투표
- 투표 방식별 UI (단일/다중 선택)
- 실시간 투표 마감 타이머
- 투표 결과 5초간 표시 후 자동 전환

### 스마트 순위 시스템
- 공동 순위 자동 처리 (동일 득표 → 같은 순위)
- 등수별 색상 구분: 🥇 금 / 🥈 은 / 🥉 동 / 4등↓ 파랑

---

## 기술 스택

- **Backend**: Flask + Python
- **Frontend**: React 17 (CDN) + Tailwind CSS + Babel
- **Storage**: Azure Cosmos DB (또는 JSON 파일 fallback)
- **Deployment**: Azure Web Apps + GitHub Actions

---

## 설치 및 실행

### 1. 의존성 설치
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 환경변수 설정
```bash
cp .env.example .env
# .env 파일을 편집하여 필요한 값 설정
```

### 3. 실행
```bash
python app.py
# http://localhost:5000
```

Cosmos DB 없이 실행하면 자동으로 `data/` 디렉토리에 JSON 파일로 저장됩니다.

---

## Azure Cosmos DB 설정

### 1. Azure Portal에서 Cosmos DB 계정 생성

1. [Azure Portal](https://portal.azure.com) 접속
2. **리소스 만들기** → **Azure Cosmos DB** 검색
3. **Azure Cosmos DB for NoSQL** 선택 → **만들기**
4. 설정:
   - **구독**: 사용할 Azure 구독 선택
   - **리소스 그룹**: 기존 그룹 선택 또는 새로 만들기
   - **계정 이름**: 고유한 이름 (예: `team-votes-cosmos`)
   - **위치**: Korea Central (한국 중부)
   - **용량 모드**: **서버리스** (소규모 사용에 적합, 비용 절감)
5. **검토 + 만들기** → **만들기**

### 2. 데이터베이스 및 컨테이너 생성

1. 생성된 Cosmos DB 계정으로 이동
2. **데이터 탐색기** → **새 데이터베이스**
   - **데이터베이스 ID**: `team-votes-db`
3. 데이터베이스 아래 **새 컨테이너**
   - **컨테이너 ID**: `team-votes`
   - **파티션 키**: `/cohort_id`
   - **처리량**: 서버리스 모드에서는 자동 (수동 설정 시 400 RU/s 권장)

### 3. 연결 키 확인

1. Cosmos DB 계정 → **키** 메뉴
2. 다음 값을 복사:
   - **URI** (= Endpoint)
   - **기본 키** (= Key)

### 4. 환경변수 설정

`.env` 파일에 다음을 추가:
```env
COSMOS_ENDPOINT=https://team-votes-cosmos.documents.azure.com:443/
COSMOS_KEY=your-primary-key-here==
COSMOS_DB=team-votes-db
COSMOS_CONTAINER=team-votes
```

### 5. 확인

앱 실행 시 콘솔에 다음 메시지가 출력되면 성공:
```
Cosmos DB initialized for team votes
```

설정하지 않으면 자동으로 JSON fallback 모드로 동작합니다:
```
Warning: azure-cosmos not installed. Using local JSON fallback.
```

### Cosmos DB 문서 구조

| Document ID | Partition Key | 내용 |
|---|---|---|
| `team_votes_cohorts` | `system` | 과정 목록 |
| `{cohort_id}_students` | `{cohort_id}` | 학생 데이터 |
| `{cohort_id}_teams` | `{cohort_id}` | 팀 데이터 |
| `{cohort_id}_votes` | `{cohort_id}` | 투표 기록 |
| `{cohort_id}_vote_config` | `{cohort_id}` | 투표 설정 |

---

## 사용 방법

### 관리자 워크플로우

1. **관리자 모드** 로그인 (기본 비밀번호: `sample`)
2. **과정 관리** 탭:
   - 과정 생성 (예: ID=`DT4`, 이름=`MS Data 4기`)
   - students.json 파일 업로드
3. **팀 관리** 탭:
   - 과정 선택 → **팀 만들기/편집** 클릭
   - 드래그앤드롭으로 학생을 팀에 배치
   - 팀명, 프로젝트명 입력 → **팀 저장**
4. **투표 제어** 탭:
   - 투표 방식 (1개/3개 팀) 및 시간 설정
   - **투표 시작** → 학생들이 투표 진행
   - 투표 종료 또는 자동 마감
5. **투표 결과** 탭:
   - 실시간 결과 확인, CSV 다운로드

### students.json 형식
```json
[
  { "id": 1, "name": "홍길동", "password": "1234" },
  { "id": 2, "name": "김철수", "password": "5678" }
]
```

### 학생 워크플로우

1. **학생 모드** → 이름 + 비밀번호 로그인
2. 투표할 팀 선택 → **투표하기**
3. 투표 결과 5초 표시 후 자동 전환

---

## API 엔드포인트

### 과정 관리
| Method | Path | 설명 |
|---|---|---|
| GET | `/api/cohorts` | 과정 목록 |
| POST | `/api/cohorts` | 과정 생성 |
| PUT | `/api/cohorts/<id>` | 과정 수정 |
| DELETE | `/api/cohorts/<id>` | 과정 삭제 |

### 학생/팀 관리
| Method | Path | 설명 |
|---|---|---|
| GET | `/api/cohorts/<id>/students` | 학생 목록 |
| POST | `/api/cohorts/<id>/students/upload` | students.json 업로드 |
| GET | `/api/cohorts/<id>/teams` | 팀 목록 |
| POST | `/api/cohorts/<id>/teams` | 팀 저장 (TeamBuilder) |

### 학생 투표
| Method | Path | 설명 |
|---|---|---|
| POST | `/api/login` | 학생 로그인 (활성 과정 자동 감지) |
| GET | `/api/teams/<cohort_id>/<student_id>` | 투표 가능 팀 |
| POST | `/api/vote` | 투표 (cohort_id 포함) |

### 관리자 투표 제어
| Method | Path | 설명 |
|---|---|---|
| POST | `/api/admin/login` | 관리자 로그인 |
| GET | `/api/admin/<cohort_id>/vote-config` | 투표 설정 조회 |
| POST | `/api/admin/<cohort_id>/start-vote` | 투표 시작 |
| POST | `/api/admin/<cohort_id>/stop-vote` | 투표 종료 |
| POST | `/api/admin/<cohort_id>/set-vote-time` | 투표 시간 설정 |
| POST | `/api/admin/<cohort_id>/reset` | 투표 초기화 |
| GET | `/api/admin/<cohort_id>/students` | 학생 현황 |
| GET | `/api/admin/<cohort_id>/teams` | 팀 현황 |
| GET | `/api/admin/<cohort_id>/votes` | 투표 결과 |
| GET | `/api/admin/<cohort_id>/download` | CSV 다운로드 |

---

## 파일 구조

```
team_votes/
├── app.py                 # Flask 메인 애플리케이션
├── cosmos_service.py      # Cosmos DB / JSON 이중 모드 서비스
├── requirements.txt       # Python 의존성
├── .env                   # 환경변수 (git 제외)
├── .env.example           # 환경변수 템플릿
├── data/                  # JSON fallback 데이터 (git 제외)
├── static/
│   ├── js/
│   │   └── main.js        # React 컴포넌트 (SPA)
│   ├── elixerr logo_resize.png
│   └── profile.png
├── templates/
│   └── index.html         # HTML 쉘 + CDN 로드
├── course/                # 레거시 과정 데이터 (참조용)
└── .github/workflows/
    └── main_team-vote.yml # Azure 배포 CI/CD
```

---

## 환경변수

| 변수 | 필수 | 기본값 | 설명 |
|---|---|---|---|
| `SECRET_KEY` | 권장 | `team-votes-secret-key` | Flask 시크릿 키 |
| `TEACHER_PASSWORD` | 권장 | `sample` | 관리자 비밀번호 |
| `COSMOS_ENDPOINT` | 선택 | - | Cosmos DB URI |
| `COSMOS_KEY` | 선택 | - | Cosmos DB 기본 키 |
| `COSMOS_DB` | 선택 | - | 데이터베이스 이름 |
| `COSMOS_CONTAINER` | 선택 | - | 컨테이너 이름 |
| `TZ` | 선택 | `Asia/Seoul` | 시간대 |

---

## 보안

### 인증 및 권한
- **세션 기반 관리자 인증**: 모든 관리 API에 `@require_admin` 데코레이터 적용
- **환경변수 비밀번호**: `TEACHER_PASSWORD`를 `.env`에서 관리 (기본값 사용 비권장)
- **Flask SECRET_KEY**: 세션 암호화를 위한 시크릿 키 설정 필수

### 입력 검증
- **cohort_id 검증**: 정규식 `^[a-zA-Z0-9_-]{1,50}$`으로 Path Traversal 방지
- **학생 데이터 검증**: 업로드 시 ID 타입(정수), 이름 필수, 중복 ID 검사, 최대 500명 제한
- **투표 시간 검증**: `duration_minutes` 범위 제한 (1~1440분)

### 파일 업로드 보안
- **업로드 크기 제한**: `MAX_CONTENT_LENGTH = 2MB`
- **JSON 형식 검증**: 파일 파싱 실패 시 거부
- **413 에러 핸들러**: 파일 크기 초과 시 명확한 에러 메시지

### 정보 노출 방지
- **에러 메시지 sanitize**: 내부 에러 상세(`str(e)`)를 클라이언트에 노출하지 않음
- **투표 수 비노출**: 학생 투표 화면에서 `vote_count` 제거 (결과 편향 방지)
- **`.env` git 제외**: `.gitignore`에 `.env` 포함하여 비밀키 커밋 방지

---

## 버전 히스토리

### v4.1.0 (최신) - 보안 강화
- **세션 기반 관리자 인증**: `@require_admin` 데코레이터로 모든 관리 엔드포인트 보호
- **Path Traversal 방지**: cohort_id 정규식 검증
- **파일 업로드 제한**: 2MB 크기 제한 + 413 에러 핸들러
- **학생 데이터 검증**: ID 타입/중복/이름/개수 검증
- **에러 메시지 sanitize**: 내부 정보 비노출
- **투표 수 비노출**: 학생 투표 UI에서 `vote_count` 제거

### v4.0.0 - Cosmos DB + 관리자 팀 빌더
- **Azure Cosmos DB 연동**: JSON fallback 이중 모드 스토리지
- **과정(코호트) 관리**: 관리자 UI에서 교육과정 생성/삭제
- **학생 업로드**: students.json 파일 업로드로 학생 등록
- **드래그앤드롭 팀 빌더**: GUI에서 팀 구성 (균등 배분, 팀명/프로젝트명 편집)
- **과정별 독립 투표**: 각 과정이 독립적으로 투표 설정/진행
- **프론트엔드 분리**: 인라인 React → static/js/main.js 추출
- **API 리팩토링**: 과정 스코프 엔드포인트 (/api/cohorts, /api/admin/<cohort_id>/...)

### v3.0.0 - 대규모 리팩토링
- 전체 코드 아키텍처 개선 (상수, API, 훅, 컴포넌트 모듈화)
- 커스텀 훅 도입 (useMessage, useCountdown, useVoteTimer 등)
- 재사용 컴포넌트 분리 (Modal, TimeSelector 등)

### v2.0.0 - 다중 투표 & 시간 관리
- 다중 투표 방식 (1개/3개 팀 선택)
- 투표 시간 관리 (즉시 시작/시간 예약)
- 실시간 마감 타이머
- 공동 순위 시스템

### v1.0.0 - 초기 버전
- 기본 투표 시스템, CSV 다운로드

---

## 라이선스

MIT License - 교육 목적으로 자유롭게 사용 가능합니다.
