<div align="center">
  <img src="assets/icon.png" width="128" height="128" alt="Focus Reader Icon">
  
  # Focus Reader 📚🧠
  
  **[🇰🇷 한국어](#한국어) | [🇺🇸 English](#english)**
</div>

---

# English

**Paper Reader for ADHD**

Breaks sentences into meaningful chunks with color highlighting and Bionic Reading for easier focus!

---

## ✨ Features at a Glance

### 📖 Smart Reading Experience
| Feature | What it Does |
|---------|--------------|
| **Chunk Highlighting** | Sentences are split into meaningful phrases with alternating colors (blue/orange) - easier to follow! |
| **Bionic Reading** | First few letters of each word are **bold** to guide your eyes naturally |
| **One Paragraph at a Time** | Click a paragraph → it opens in a focused reader view, no distractions |
| **Keyboard Navigation** | Use `←` `→` to move between sentences, `↑` `↓` to jump paragraphs |

### 🎧 Audio Features
| Feature | What it Does |
|---------|--------------|
| **Text-to-Speech** | Listen to paragraphs with natural AI voices |
| **Sentence Sync** | Audio highlights the current sentence as it plays |
| **3 TTS Options** | Kokoro (free/local), OpenAI (premium), or Browser TTS |
| **Playback Controls** | Play/pause, skip sentences, adjust speed |

### 🗂️ Library & Organization
| Feature | What it Does |
|---------|--------------|
| **PDF Library** | All your papers in one place with thumbnails |
| **Folders** | Create folders to organize papers by topic |
| **Search** | Find papers by title |
| **Reading Progress** | Resume where you left off |

### 🤖 AI Assistant (Optional)
| Feature | What it Does |
|---------|--------------|
| **Claude Chat** | Ask questions about the paper, get summaries |
| **Context-Aware** | AI knows which paragraph you're reading |

### 🎨 UI Overview
<img width="1371" height="839" alt="Screenshot 2025-11-27 at 09 58 05" src="https://github.com/user-attachments/assets/20abbfb4-b9b2-4bdb-9b1e-ed9bcfcd03b0" />


---

## 🚀 Installation (Mac)

### Option 1: DMG File (Easy)

#### Step 1: Install Prerequisites

**Docker Desktop:**
1. Go to https://www.docker.com/products/docker-desktop/
2. Click **"Download for Mac"** → Download
3. Double-click the downloaded file to install
4. Run **Docker** from Applications (whale icon 🐳)
5. Wait until Docker is fully started (whale stops moving in menu bar)

#### Step 2: Start Services

Open Terminal and run:

\`\`\`bash
# Clone and start with Docker Compose
git clone https://github.com/thgud1624/focus-reader.git
cd focus-reader
docker-compose up -d
\`\`\`

> ⏳ First time takes 5-10 minutes to download!

This starts:
- **Grobid** (port 8070) - PDF parsing
- **spaCy** (port 8000) - Sentence chunking
- **Kokoro TTS** (port 8001) - Free local TTS

#### Step 3: Install Focus Reader

1. Download **Focus Reader.dmg** from [Releases](https://github.com/thgud1624/focus-reader/releases)
2. Double-click the DMG file
3. Drag Focus Reader to **Applications** folder
4. Run Focus Reader from Applications!

---

### Option 2: Build from Source (Developers)

\`\`\`bash
git clone https://github.com/thgud1624/focus-reader.git
cd focus-reader
npm install
docker-compose up -d
npm start
\`\`\`

---

## 🎮 Usage

1. **Open PDF**: Select a PDF file in the app
2. **Click Paragraph**: Click on a paragraph you want to read
3. **Navigate Sentences**: Use arrow keys \`←\` \`→\` or \`↑\` \`↓\`

---

## 🎙️ TTS Options

| Engine | Cost | Quality | Requirements |
|--------|------|---------|--------------|
| **Kokoro TTS** | Free | Good | Docker running |
| **OpenAI TTS** | ~\$15/1M chars | Excellent | API key |

> 💡 Kokoro TTS runs locally via Docker - completely free!

---

## 🔑 API Keys (Optional)

### Claude API
> For AI chat features

1. Go to https://console.anthropic.com
2. Create API key
3. Click **[🔑 API]** in app → Enter key

### OpenAI API
> For premium TTS (optional - Kokoro is free)

1. Go to https://platform.openai.com
2. Create API key
3. Click **[🔑 API]** in app → Enter OpenAI key

**Features without API keys:**
- ✅ PDF reading & navigation
- ✅ Bionic Reading & color highlighting
- ✅ Kokoro TTS (free, local)
- ✅ Notes

**Features requiring API keys:**
- 🔑 Claude AI chat (Claude API)
- 🔑 OpenAI TTS (OpenAI API)

---

## ❓ Troubleshooting

### App won't open / "Damaged app" warning
\`\`\`bash
xattr -cr /Applications/Focus\\ Reader.app
\`\`\`

### "docker: command not found"
→ Docker Desktop not installed or not running

### PDF parsing fails
→ Check Docker is running (whale icon 🐳)
→ Run: \`docker-compose up -d\`
→ Verify: \`docker ps\` should show grobid, spacy, kokoro

---

## 🌐 Language

The app supports **English** and **Korean**. Toggle in the header:
- Click \`한국어\` for Korean
- Click \`ENG\` for English

---

# 한국어

**ADHD를 위한 논문 리더**

문장을 의미 단위로 쪼개서 색깔로 보여주고, Bionic Reading으로 읽기 쉽게 해줘요!

## 🚀 설치 방법 (Mac)

### 방법 1: DMG 파일로 설치 (쉬움)

#### 1단계: 필수 프로그램 설치

**Docker Desktop 설치:**
1. https://www.docker.com/products/docker-desktop/ 접속
2. **"Download for Mac"** 클릭 → 다운로드
3. 다운받은 파일 더블클릭해서 설치
4. Applications에서 **Docker** 실행 (고래 아이콘 🐳)
5. Docker가 완전히 켜질 때까지 기다리기 (상단바에 고래가 움직임 멈추면 OK)

#### 2단계: 서비스 시작

터미널 열고:

\`\`\`bash
# 레포 클론 후 Docker Compose로 시작
git clone https://github.com/thgud1624/focus-reader.git
cd focus-reader
docker-compose up -d
\`\`\`

> ⏳ 처음엔 다운로드 때문에 5~10분 걸려요!

이렇게 하면 다음 서비스들이 시작돼요:
- **Grobid** (포트 8070) - PDF 파싱
- **spaCy** (포트 8000) - 문장 청킹
- **Kokoro TTS** (포트 8001) - 무료 로컬 TTS

#### 3단계: Focus Reader 설치

1. [Releases](https://github.com/thgud1624/focus-reader/releases)에서 **Focus Reader.dmg** 다운로드
2. DMG 파일 더블클릭
3. Focus Reader 앱을 **Applications** 폴더로 드래그
4. Applications에서 Focus Reader 실행!

---

### 방법 2: 소스코드로 설치 (개발자용)

\`\`\`bash
git clone https://github.com/thgud1624/focus-reader.git
cd focus-reader
npm install
docker-compose up -d
npm start
\`\`\`

---

## 🎮 사용법

1. **PDF 열기**: 앱에서 PDF 파일 선택
2. **문단 클릭**: PDF에서 읽고싶은 문단 클릭
3. **문장 이동**: 방향키 \`←\` \`→\` 또는 \`↑\` \`↓\`

---

## 🎙️ TTS 옵션

| 엔진 | 비용 | 품질 | 요구사항 |
|------|------|------|----------|
| **Kokoro TTS** | 무료 | 좋음 | Docker 실행 |
| **OpenAI TTS** | ~\$15/1M 글자 | 최고 | API 키 |

> 💡 Kokoro TTS는 Docker로 로컬에서 실행 - 완전 무료!

---

## 🔑 API 키 설정 (선택사항)

### Claude API
> AI 챗 기능용

1. https://console.anthropic.com 접속
2. API 키 생성
3. 앱에서 **[🔑 API]** 버튼 클릭 → 키 입력

### OpenAI API
> 프리미엄 TTS용 (Kokoro는 무료)

1. https://platform.openai.com 접속
2. API 키 생성
3. 앱에서 **[🔑 API]** 버튼 클릭 → OpenAI 키 입력

**API 키 없이도 가능한 기능:**
- ✅ PDF 열기 & 읽기
- ✅ Bionic Reading & 색깔 하이라이트
- ✅ Kokoro TTS (무료, 로컬)
- ✅ 노트 작성

**API 키 필요한 기능:**
- 🔑 Claude AI 챗 (Claude API)
- 🔑 OpenAI TTS (OpenAI API)

---

## ❓ 문제 해결

### 앱이 안 열려요 / "손상된 앱" 경고
\`\`\`bash
xattr -cr /Applications/Focus\\ Reader.app
\`\`\`

### "docker: command not found"
→ Docker Desktop 설치 안 됨 / 안 켜짐

### PDF 파싱이 안 돼요
→ Docker Desktop이 켜져있는지 확인 (고래 아이콘 🐳)
→ 실행: \`docker-compose up -d\`
→ 확인: \`docker ps\` 쳤을 때 grobid, spacy, kokoro 보여야 함

---

## 🌐 언어 설정

앱은 **영어**와 **한국어**를 지원합니다. 헤더에서 토글:
- \`한국어\` 클릭하면 한국어
- \`ENG\` 클릭하면 영어

---

## 💾 데이터 저장

| 항목 | 저장 위치 | 설명 |
|------|----------|------|
| API 키 | 앱 내 localStorage | 로컬에만 저장, 외부 전송 안 함 |
| 노트 | 앱 내 저장소 | 논문별 메모 |
| UI 상태 | localStorage | 패널 펼침/접힘 상태 |

---

## ☕ Support

이 프로젝트가 도움이 되셨다면 커피 한 잔 사주세요!

If this project helped you, consider buying me a coffee!

---

## 📜 License

This project is proprietary software. See [LICENSE](LICENSE) for details.

- ✅ Personal non-commercial use allowed / 개인 비상업적 사용 허용
- ❌ Commercial use, modification, redistribution prohibited / 상업적 사용, 수정, 재배포 금지

---

Made with ❤️ for ADHD
