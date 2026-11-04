"""
Jarvis AI Agent - Starter Framework
Features: Voice STT, TTS, LLM, System automation
"""
import os
import sys
import json
import subprocess
import webbrowser
import yaml
import pyttsx3
import speech_recognition as sr
import psutil
import pyautogui
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class JarvisAgent:
    def __init__(self, config_path="config.yaml"):
        self.config = self._load_config(config_path)
        self.name = self.config.get("agent", {}).get("name", "Jarvis")
        self.wake_phrase = self.config.get("wake_word", {}).get("phrase", "hey jarvis").lower()
        self.wake_enabled = self.config.get("wake_word", {}).get("enabled", True)

        self.tts = pyttsx3.init()
        self.tts.setProperty("rate", self.config.get("agent", {}).get("rate", 180))
        self.tts.setProperty("volume", self.config.get("agent", {}).get("volume", 1.0))

        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()

        self.llm_provider = self.config.get("llm", {}).get("provider", "ollama")
        self.llm_model = self.config.get("llm", {}).get("model", "llama3")
        self.llm_base_url = self.config.get("llm", {}).get("base_url", "http://localhost:11434")

        print(f"?? {self.name} initialized. Provider: {self.llm_provider}")

    def _load_config(self, path):
        if not os.path.exists(path):
            print(f"?? Config {path} not found. Using defaults.")
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def speak(self, text):
        print(f"??? {self.name}: {text}")
        self.tts.say(text)
        self.tts.runAndWait()

    def listen(self, timeout=5, phrase_time_limit=7):
        with self.microphone as source:
            print("?? Listening...")
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                text = self.recognizer.recognize_google(audio)
                print(f"?? You: {text}")
                return text.lower()
            except sr.WaitTimeoutError:
                print("?? Listening timed out.")
                return ""
            except sr.UnknownValueError:
                print("? Could not understand audio.")
                return ""
            except sr.RequestError as e:
                print(f"? STT service error: {e}")
                return ""

    def ask_llm(self, prompt):
        if self.llm_provider == "ollama":
            return self._ollama_chat(prompt)
        elif self.llm_provider == "openai":
            return self._openai_chat(prompt)
        else:
            return self._stub_response(prompt)

    def _ollama_chat(self, prompt):
        import requests
        try:
            payload = {
                "model": self.llm_model,
                "prompt": prompt,
                "stream": False
            }
            resp = requests.post(f"{self.llm_base_url}/api/generate", json=payload, timeout=60)
            if resp.status_code == 200:
                return resp.json().get("response", "No response from Ollama.")
            return f"Ollama error: {resp.status_code}"
        except Exception as e:
            return f"Ollama connection failed: {e}. Make sure Ollama is running."

    def _openai_chat(self, prompt):
        import requests
        api_key = self.config.get("llm", {}).get("openai_api_key") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            return "OpenAI API key not configured."
        try:
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            data = {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": prompt}]
            }
            resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data, timeout=60)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            return f"OpenAI error: {resp.status_code}"
        except Exception as e:
            return f"OpenAI request failed: {e}"

    def _stub_response(self, prompt):
        responses = {
            "hello": f"Hello! I am {self.name}. How can I help you?",
            "who are you": f"I am {self.name}, your personal AI assistant.",
            "time": f"The current time is {datetime.now().strftime('%I:%M %p')}",
            "date": f"Today is {datetime.now().strftime('%B %d, %Y')}",
        }
        for key, val in responses.items():
            if key in prompt:
                return val
        return "I'm running in stub mode. Configure Ollama or OpenAI in config.yaml to enable real AI."

    def open_app(self, app_name):
        app_name = app_name.lower()
        try:
            if "notepad" in app_name:
                subprocess.Popen(["notepad.exe"])
                return "Opening Notepad."
            elif "calculator" in app_name or "calc" in app_name:
                subprocess.Popen(["calc.exe"])
                return "Opening Calculator."
            elif "chrome" in app_name or "browser" in app_name:
                subprocess.Popen(["chrome.exe"])
                return "Opening Chrome."
            elif "command prompt" in app_name or "cmd" in app_name:
                subprocess.Popen(["cmd.exe"])
                return "Opening Command Prompt."
            elif "task manager" in app_name:
                subprocess.Popen(["taskmgr.exe"])
                return "Opening Task Manager."
            else:
                return f"Sorry, I don't know how to open {app_name}."
        except Exception as e:
            return f"Failed to open {app_name}: {e}"

    def open_website(self, site):
        site = site.lower().strip()
        if not site.startswith("http"):
            site = "https://www." + site + ".com"
        webbrowser.open(site)
        return f"Opening {site}"

    def system_info(self):
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        return f"CPU usage is {cpu}% and memory usage is {mem}%."

    def shutdown(self, seconds=60):
        os.system(f"shutdown /s /t {seconds}")
        return f"System will shut down in {seconds} seconds."

    def abort_shutdown(self):
        os.system("shutdown /a")
        return "Shutdown aborted."

    def handle_command(self, text):
        text = text.lower()
        if self.wake_enabled and self.wake_phrase not in text:
            return None
        command = text.replace(self.wake_phrase, "").strip()
        if not command:
            return f"Yes, I am listening. How can I help you?"
        if "open" in command:
            for app in ["notepad", "calculator", "calc", "chrome", "browser", "command prompt", "cmd", "task manager"]:
                if app in command:
                    return self.open_app(command.replace("open", "").replace(app, "").strip() or app)
            if any(w in command for w in ["website", "site", "google", "youtube", "facebook"]):
                return self.open_web_from_text(command)
            return "Please specify what you want to open."
        if "time" in command or "date" in command:
            return self.ask_llm(command)
        if "shutdown" in command:
            return self.shutdown()
        if "abort" in command and "shutdown" in command:
            return self.abort_shutdown()
        if "system info" in command or "cpu" in command or "memory" in command:
            return self.system_info()
        return self.ask_llm(command)

    def open_web_from_text(self, text):
        if "google" in text:
            return self.open_website("google.com")
        if "youtube" in text:
            return self.open_website("youtube.com")
        if "facebook" in text:
            return self.open_website("facebook.com")
        return self.open_website(text)

    def run(self):
        self.speak(f"Hello! I am {self.name}. Your personal AI assistant is ready.")
        print("?? Say 'exit' or 'quit' to stop.\n")
        while True:
            text = self.listen()
            if not text:
                continue
            if any(w in text for w in ["exit", "quit", "stop", "goodbye"]):
                self.speak("Goodbye! Have a great day.")
                break
            response = self.handle_command(text)
            if response:
                self.speak(response)


if __name__ == "__main__":
    jarvis = JarvisAgent()
    jarvis.run()
