<div align="center">
  <img src="assets/icon.png" width="128" height="128" alt="Focus Reader Icon">
  
  # Focus Reader 📚🧠
  
  **ADHD를 위한 논문 리더**
  
  문장을 의미 단위로 쪼개서 색깔로 보여주고, Bionic Reading으로 읽기 쉽게 해줘요!
</div>

---

## 🚀 설치 방법 (Mac 기준)

### 1단계: Docker Desktop 설치

1. https://www.docker.com/products/docker-desktop/ 접속
2. **"Download for Mac"** 클릭해서 다운로드
3. 다운받은 파일 실행해서 설치
4. 설치 후 Docker Desktop 앱 실행 (고래 아이콘 🐳)

### 2단계: Grobid 실행 (PDF 파싱용)

터미널 열고 (Spotlight에서 "터미널" 검색):

```bash
docker run -d --name grobid --restart=always -p 8070:8070 lfoppiano/grobid:0.8.0
```

> ⏳ 처음엔 다운로드 때문에 몇 분 걸려요. 기다리세요!
> 
> ✅ 완료되면 \`docker ps\` 치면 grobid가 보여요.

### 3단계: Python 패키지 설치

터미널에서:

```bash
pip3 install fastapi uvicorn httpx spacy
python3 -m spacy download en_core_web_sm
```

### 4단계: Node.js 설치

1. https://nodejs.org/ 접속
2. **LTS 버전** 다운로드 & 설치

### 5단계: Focus Reader 다운로드 & 실행

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
3. **문장 이동**: 방향키 \`←\` \`→\` 또는 \`↑\` \`↓\`로 문장 이동

---

## ❓ 문제 해결

### "docker: command not found"
→ Docker Desktop이 설치 안 됨. 1단계부터 다시!

### "pip3: command not found"  
→ Python 설치 필요. https://www.python.org/downloads/ 에서 설치

### "npm: command not found"
→ Node.js 설치 필요. 4단계 다시!

### Grobid가 안 돌아요
```bash
docker start grobid
```

### 앱이 PDF를 못 읽어요
→ Grobid가 실행 중인지 확인:
```bash
docker ps
```
grobid가 안 보이면 2단계 다시!

---

## 🔄 매일 사용할 때

1. **Docker Desktop 실행** (고래 아이콘)
2. 터미널에서:
```bash
cd focus-reader
npm start
```

> 💡 Grobid는 \`--restart=always\` 옵션 덕분에 Docker 켜면 자동 실행돼요!

---

Made with ❤️ for ADHD
