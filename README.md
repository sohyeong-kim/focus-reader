<div align="center">
  <img src="assets/icon.png" width="128" height="128" alt="Focus Reader Icon">
  
  # Focus Reader 📚🧠
  
  **ADHD-friendly research paper reader with semantic chunking and Bionic Reading**
  
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
  [![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-blue)]()
</div>

---

## ✨ Features

### 🎯 ADHD-Friendly Reading
- **Semantic Chunking**: Sentences are automatically split into meaningful chunks with color-coded highlights
- **Bionic Reading**: First part of each word is bolded to guide your eyes naturally
- **Sentence-by-sentence navigation**: Focus on one sentence at a time with keyboard shortcuts

### 📄 PDF Intelligence
- **Grobid ML Parser**: Advanced PDF parsing that understands paper structure
- **Click-to-read**: Click any paragraph in the PDF to start reading
- **Multi-column support**: Works with two-column academic papers
- **Section browser**: Navigate by paper sections

### 🤖 AI Assistant
- **Claude Integration**: Chat with Claude about the paper you're reading
- **Context-aware**: AI knows which paragraph you're focusing on

### 📝 Note Taking
- **Per-paper notes**: Notes are saved for each paper automatically
- **Persistent storage**: Your notes survive app restarts

---

## 🖼️ Screenshots

<div align="center">
  <img src="docs/screenshot-main.png" width="800" alt="Main Interface">
  <p><em>Main reading interface with semantic chunking</em></p>
</div>

---

## 🚀 Installation

### Prerequisites

1. **Docker** (for Grobid PDF parser)
   ```bash
   # Install Docker Desktop from https://docker.com
   ```

2. **Python 3.10+** with packages:
   ```bash
   pip install fastapi uvicorn httpx spacy
   python -m spacy download en_core_web_sm
   ```

3. **Node.js 18+** (for development)
   ```bash
   # Install from https://nodejs.org
   ```

### Quick Start

1. **Start Grobid** (PDF parser):
   ```bash
   # First time - download and run (takes a few minutes)
   docker run -d --name grobid --restart=always -p 8070:8070 lfoppiano/grobid:0.8.0
   ```
   
   > 💡 **Docker Tips:**
   > - `--restart=always` makes Grobid start automatically when your computer boots
   > - Check if running: `docker ps`
   > - If stopped, restart with: `docker start grobid`
   > - Stop it: `docker stop grobid`

2. **Clone and install**:
   ```bash
   git clone https://github.com/thgud1624/focus-reader.git
   cd focus-reader
   npm install
   ```

3. **Run the app**:
   ```bash
   npm start
   ```

### Download Pre-built App

> Coming soon! Check the [Releases](https://github.com/thgud1624/focus-reader/releases) page.

---

## 🎮 Usage

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `←` / `↑` | Previous sentence |
| `→` / `↓` | Next sentence |
| Click PDF | Select paragraph |

### Reading Flow

1. **Open a PDF**: Click the file input or drag & drop
2. **Wait for parsing**: Grobid analyzes the paper structure
3. **Click a paragraph**: The text appears in the right panel
4. **Navigate sentences**: Use arrow keys to move through sentences
5. **Take notes**: Write notes in the Notes section
6. **Ask Claude**: Chat with AI about what you're reading

---

## 🛠️ Development

### Project Structure

```
focus-reader/
├── main.js              # Electron main process
├── preload.js           # Electron preload script
├── focusread-v5.html    # Main app (single HTML file)
├── server_grobid_v2.py  # Python backend (Grobid + spaCy)
├── assets/
│   ├── icon.svg         # App icon source
│   ├── icon.png         # PNG icon
│   └── icon.icns        # macOS icon
└── package.json
```

### Building

```bash
# Build for current platform
npm run build

# Build for specific platform
npm run build:mac
npm run build:win
npm run build:linux
```

### Tech Stack

- **Frontend**: Vanilla JS, PDF.js, HTML/CSS
- **Backend**: FastAPI, spaCy (NLP), Grobid (PDF parsing)
- **Desktop**: Electron
- **AI**: Claude API (Anthropic)

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📋 Requirements

### System Requirements
- macOS 10.15+ / Windows 10+ / Ubuntu 20.04+
- 4GB RAM minimum
- 500MB disk space

### Runtime Dependencies
- Docker (for Grobid)
- Python 3.10+
- Internet connection (for Claude AI)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [Grobid](https://github.com/kermitt2/grobid) - Machine learning PDF parser
- [spaCy](https://spacy.io/) - Industrial-strength NLP
- [PDF.js](https://mozilla.github.io/pdf.js/) - PDF rendering
- [Bionic Reading](https://bionic-reading.com/) - Reading technique inspiration
- [Anthropic Claude](https://anthropic.com/) - AI assistant

---

<div align="center">
  Made with ❤️ for people with ADHD
  
  **Focus on what matters. One sentence at a time.**
</div>
