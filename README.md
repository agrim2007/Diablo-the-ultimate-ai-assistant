# 🔥 DIABLO — Ultimate AI Desktop Assistant

> **A wake-word-free, voice-controlled AI assistant for Windows.** Speak directly to open files, launch apps, and navigate websites — all with natural language commands and SAPI5 text-to-speech feedback.

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![Windows](https://img.shields.io/badge/platform-Windows-blue.svg)](https://www.microsoft.com/windows)
[![pyttsx3](https://img.shields.io/badge/TTS-pyttsx3%20%7C%20SAPI5-green.svg)](https://pypi.org/project/pyttsx3/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 📑 Table of Contents

- [About](#about)
- [Problem Statement](#problem-statement)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Usage](#usage)
- [License](#license)
- [Author](#author)

---

## 🎯 About

**DIABLO** is a personal AI desktop assistant built for Windows. Unlike traditional voice assistants that require a wake word (e.g., "Hey Siri", "Alexa"), DIABLO listens for direct commands and responds instantly. It uses **pyttsx3 with SAPI5** for text-to-speech, processes speech-to-text input, and can open local files, folders, installed applications, and websites — all through voice or text.

## 🛠 Problem Statement

Most desktop assistants are either cloud-heavy, require a wake word, or lack deep OS integration. DIABLO solves this by:

- Removing the wake-word barrier for faster, direct interaction
- Integrating tightly with Windows file system, Start Menu, and registry
- Providing fuzzy voice-to-file matching so imprecise speech still works
- Auto-detecting OneDrive-redirected folders (Desktop, Documents, Downloads)
- Running locally with optional AI backends (Ollama or OpenAI)

---

## ✨ Features

- **🎙️ Wake-word-free voice commands** — Speak directly; no trigger phrase needed
- **🔊 SAPI5 Text-to-Speech** — Natural spoken responses via `pyttsx3`
- **📂 Open files & folders** — Fuzzy matching across Desktop, Downloads, Documents (including OneDrive paths)
- **💻 Launch installed apps** — Scans Start Menu + Windows registry (130+ applications)
- **🌐 Open websites** — Direct URL or domain-hint based web launching
- **❓ Ambiguity handling** — When multiple files match, DIABLO asks you to specify the extension
- **🔧 Configurable** — `config.yaml` for AI provider, model, wake word, and behavior
- **🧩 Stub & AI modes** — Falls back to stub responses when no AI provider is configured

---

## 🧰 Tech Stack

| Category | Technology |
|----------|------------|
| Language | Python 3.11 |
| TTS Engine | pyttsx3 (Microsoft SAPI5) |
| Speech Recognition | SpeechRecognition |
| AI Provider | Ollama (local) or OpenAI (cloud) |
| Config | YAML (`config.yaml`) |
| OS Integration | Windows API, Start Menu, Registry |
| Platform | Windows 10 / 11 |

---

## 🏗 Architecture

```text
┌─────────────┐      ┌──────────────────┐      ┌─────────────────┐
│   User      │─────▶│  Speech-to-Text  │─────▶│  handle_command │
│  (Voice /   │      │  (Microphone)    │      │  (Router)       │
│   Text)     │      └──────────────────┘      └────────┬────────┘
└─────────────┘                                         │
                                                        ▼
┌─────────────┐                              ┌─────────────────────┐
│   TTS       │◄────────────────────────────│  Response / Action  │
│ (pyttsx3)   │                              │                     │
└─────────────┘                              ├─▶ Open File / Folder│
                                              ├─▶ Launch App        │
                                              ├─▶ Open Website      │
                                              └─▶ AI / Stub Reply   │
```

**Data flow:** Voice input → STT transcription → Command router → File/App/Web resolver → Action executed → TTS response spoken back.

---

## 🚀 Getting Started

### Prerequisites

- **Windows 10 or 11** (SAPI5 TTS is Windows-specific)
- **Python 3.11+**
- A working microphone (for voice input)
- Ollama installed locally **or** an OpenAI API key (for AI-powered responses)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/<your-username>/Diablo-the-ultimate-ai-assistant.git
cd Diablo-the-ultimate-ai-assistant

# 2. Create and activate a virtual environment (recommended)
python -m venv .venv
.\.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure the assistant
# Copy or create config.yaml (see Configuration section below)
```

### Configuration

Create a `config.yaml` in the project root:

```yaml
# config.yaml
ai:
  provider: ollama       # 'ollama' | 'openai' | 'stub'
  model: llama3          # model name for ollama/openai
  api_key: ""            # required if provider is openai

wake_word:
  enabled: false         # DIABLO runs wake-word-free by default
  token: "hey jarvis"

tts:
  engine: pyttsx3        # SAPI5 backend
  rate: 180              # words per minute
  volume: 1.0            # 0.0 to 1.0
```

> **Note:** `config.yaml` is gitignored by default so your API keys stay local.

### Running the Assistant

```bash
python main.py
```

You should see:

```
?? Diablo initialized.
   Provider: ollama
   Model: llama3
   Wake word: 'hey jarvis'
??? Diablo: Hello! I am Diablo. Your personal AI assistant is ready.
?? Say 'exit' or 'quit' to stop.

?? Listening...
```

Speak commands like:

> `open profile.pdf from desktop`  
> `open chrome`  
> `open flipkart.com`

---

## ⚙️ Configuration Reference

| Key | Description | Default |
|-----|-------------|---------|
| `ai.provider` | AI backend: `ollama`, `openai`, or `stub` | `ollama` |
| `ai.model` | Model name | `llama3` |
| `ai.api_key` | OpenAI API key (if applicable) | `""` |
| `wake_word.enabled` | Require wake word before listening | `false` |
| `wake_word.token` | Wake word phrase | `hey jarvis` |
| `tts.rate` | Speech speed (WPM) | `180` |
| `tts.volume` | Volume level (0.0–1.0) | `1.0` |

---

## 💻 Usage

Once running, DIABLO listens continuously. Example voice commands:

| Command | Action |
|---------|--------|
| `open profile.pdf from desktop` | Opens `Profile.pdf` on Desktop |
| `open dbms 2.txt` | Fuzzy-opens matching text file |
| `open chrome` | Launches Google Chrome from installed apps |
| `open flipkart.com` | Opens Flipkart in default browser |
| `exit` or `quit` | Shuts down DIABLO |

If multiple files match a spoken name, DIABLO responds:

> `Multiple files match 'dbms 2': dbms 2, dbms 2.txt. Please specify extension (e.g. pdf or docx).`

### Visual Demo (Placeholder)

```markdown
![DIABLO in action](docs/assets/demo.gif)
```

> Add a screen recording or GIF under `docs/assets/demo.gif` to showcase voice interactions.

---

## 📄 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

```text
MIT License

Copyright (c) 2026 Ajay Pratap

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 👤 Author

**Ajay Pratap Singh**

- GitHub: https://github.com/pratapajaysingh
- LinkedIn: https://www.linkedin.com/in/ajay-pratap-singh-rawat-2b2902394/

**Agrim Jain**

- GitHub: https://github.com/agrim2007
- LinkedIn: https://www.linkedin.com/in/agrim-jain-0ab586375/


---

> Built with ❤️ for hands-free Windows productivity.


