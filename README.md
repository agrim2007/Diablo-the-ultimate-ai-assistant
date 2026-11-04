# Jarvis AI Agent

A personal AI assistant inspired by Iron Man's J.A.R.V.I.S., built in Python.

## Quick Start

### 1. Install dependencies
`ash
cd jarvis_agent
pip install -r requirements.txt
`

### 2. Choose your LLM backend

**Option A: Ollama (Recommended - Local & Free)**
- Install Ollama from https://ollama.com
- Run: ollama pull llama3

**Option B: OpenAI API**
- Set provider: openai in config.yaml

**Option C: Stub mode**
- provider: stub

### 3. Run
`ash
python main.py
`

Say "Hey Jarvis" followed by your command.

## Example Commands
- "Hey Jarvis, open notepad"
- "Hey Jarvis, open youtube"
- "Hey Jarvis, what is the time"
- "Hey Jarvis, system info"

## Make It Outstanding
- Screen Awareness (OCR + screenshot)
- Offline-first Voice (faster-whisper)
- Personal Memory (ChromaDB)
- Multi-agent system
