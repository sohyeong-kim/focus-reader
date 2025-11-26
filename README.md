<div align="center">
  <img src="assets/icon.png" width="128" height="128" alt="Focus Reader Icon">
  
  # Focus Reader 📚🧠
  
  **ADHD를 위한 논문 리더**
  
  문장을 의미 단위로 쪼개서 색깔로 보여주고, Bionic Reading으로 읽기 쉽게 해줘요!
</div>

---

## 🚀 설치 방법 (Mac)

### 방법 1: DMG 파일로 설치 (쉬움)

#### 1단계: 필수 프로그램 설치

**Docker Desktop 설치:**
1. https://www.docker.com/products/docker-desktop/ 접속
2. **"Download for Mac"** 클릭 → 다운로드
3. 다운받은 파일 더블클릭해서 설치
4. Applications에서 **Docker** 실행 (고래 아이콘 🐳)
5. Docker가 완전히 켜질 때까지 기다리기 (상단바에 고래가 움직임 멈추면 OK)

**Python 패키지 설치:**

터미널 열고 (Spotlight에서 "터미널" 검색) 아래 복붙:

```bash
pip3 install fastapi uvicorn httpx spacy
python3 -m spacy download en_core_web_sm
```

**Grobid 실행:**

터미널에서:

```bash
docker run -d --name grobid --restart=always -p 8070:8070 lfoppiano/grobid:0.8.0
```

> ⏳ 처음엔 다운로드 때문에 5~10분 걸려요!

#### 2단계: Focus Reader 설치

1. [Releases](https://github.com/thgud1624/focus-reader/releases)에서 **Focus Reader.dmg** 다운로드
2. DMG 파일 더블클릭
3. Focus Reader 앱을 **Applications** 폴더로 드래그
4. Applications에서 Focus Reader 실행!

---

### 방법 2: 소스코드로 설치 (개발자용)

#### 1단계: 필수 프로그램

위 방법 1의 "필수 프로그램 설치" 똑같이 하고,

**추가로 Node.js 설치:**
1. https://nodejs.org/ 접속
2. **LTS 버전** 다운로드 & 설치

#### 2단계: 다운로드 & 실행

터미널에서:

```bash
git clone https://github.com/thgud1624/focus-reader.git
cd focus-reader
npm install
npm start
```

---

## 🎮 사용법

1. **PDF 열기**: 앱에서 PDF 파일 선택
2. **문단 클릭**: PDF에서 읽고싶은 문단 클릭
3. **문장 이동**: 방향키 \`←\` \`→\` 또는 \`↑\` \`↓\`

---

## 🔑 Claude API (선택사항)

> ⚠️ **AI 챗 기능**을 사용하려면 Claude API 키가 필요해요!

**API 키 발급:**
1. https://console.anthropic.com 접속
2. 회원가입 후 API Keys에서 키 생성
3. 앱에서 **[🔑 API]** 버튼 클릭 → 키 입력

**API 키 없이도 가능한 기능:**
- ✅ PDF 열기 & 읽기
- ✅ 문단 클릭 & 문장 이동
- ✅ Bionic Reading & 색깔 하이라이트
- ✅ 노트 작성

**API 키 필요한 기능:**
- 🔑 Claude AI 챗

---

## ❓ 문제 해결

### 앱이 안 열려요 / "손상된 앱" 경고
```bash
xattr -cr /Applications/Focus\ Reader.app
```
터미널에 위 명령어 치고 다시 열기

### "docker: command not found"
→ Docker Desktop 설치 안 됨 / 안 켜짐

### "pip3: command not found"
→ Python 설치: https://www.python.org/downloads/

### PDF 파싱이 안 돼요 / "Grobid 실패"
→ Docker Desktop이 켜져있는지 확인 (고래 아이콘 ��)
→ Grobid 확인: \`docker ps\` 쳤을 때 grobid 보여야 함
→ 안 보이면: \`docker start grobid\`

---

## 🔄 매일 사용할 때

1. **Docker Desktop 실행** (고래 아이콘)
2. **Focus Reader 실행**

> 💡 Grobid는 Docker 켜면 자동 실행돼요!

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

<a href="https://buymeacoffee.com/YOUR_USERNAME" target="_blank">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="50">
</a>

- 무료로 사용하셔도 됩니다!
- 후원은 개발 동기 부여가 됩니다 🙏

---

## 📜 License

This project is proprietary software. See [LICENSE](LICENSE) for details.

- ✅ 개인 비상업적 사용 허용
- ❌ 상업적 사용, 수정, 재배포 금지

---

Made with ❤️ for ADHD
