"""
Jarvis AI Agent - Starter Framework
Features: Voice STT, TTS, LLM, System automation
"""
import os
import sys
import json
import glob
import subprocess
import webbrowser
import winreg
import platform
import yaml
import contextlib
import pyttsx3
import speech_recognition as sr
import psutil
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@contextlib.contextmanager
def suppress_c_stderr():
    """Suppress C-level stderr (e.g., ALSA / PyAudio warning spam)."""
    import contextlib as _ctx
    # Redirect OS-level file descriptor 2 to /dev/null
    devnull = os.open(os.devnull, os.O_WRONLY)
    old_stderr_fd = os.dup(2)
    os.dup2(devnull, 2)
    os.close(devnull)
    # Also redirect Python-level stderr
    old_stderr = sys.stderr
    sys.stderr = open(os.devnull, "w")
    try:
        with _ctx.redirect_stderr(sys.stderr):
            yield
    finally:
        sys.stderr = old_stderr
        os.dup2(old_stderr_fd, 2)
        os.close(old_stderr_fd)


# Try to quiet ALSA at the library level before anything audio-related loads
os.environ.setdefault("ALSA_PCM_CARD", "default")
os.environ.setdefault("ALSA_PCM_DEVICE", "0")


class JarvisAgent:
    def __init__(self, config_path="config.yaml"):
        self.config = self._load_config(config_path)
        self.name = self.config.get("agent", {}).get("name", "Jarvis")
        self.wake_phrase = self.config.get("wake_word", {}).get("phrase", "hey jarvis").lower()
        self.wake_enabled = self.config.get("wake_word", {}).get("enabled", True)

        # Installed apps survey (Start Menu shortcuts + registry uninstall)
        self.app_map = {}
        try:
            self.app_map = self._scan_installed_apps()
        except Exception:
            self.app_map = {}

        self.recognizer = sr.Recognizer()
        try:
            self.microphone = sr.Microphone()
            self._mic_available = True
        except Exception as e:
            print(f"? Microphone not available: {e}")
            print("   Falling back to text input mode.")
            self.microphone = None
            self._mic_available = False

        self.llm_provider = self.config.get("llm", {}).get("provider", "ollama")
        self.llm_model = self.config.get("llm", {}).get("model", "llama3")
        self.llm_base_url = self.config.get("llm", {}).get("base_url", "http://localhost:11434")

        # STT configuration
        self.stt_provider = self.config.get("stt", {}).get("provider", "whisper")
        self.whisper_model_name = self.config.get("stt", {}).get("model", "base")
        self._whisper_model = None

        print(f"?? {self.name} initialized.")
        print(f"   Provider: {self.llm_provider}")
        print(f"   Model: {self.llm_model}")
        print(f"   Wake word: '{self.wake_phrase}'")

    def _load_config(self, path):
        if not os.path.exists(path):
            print(f"?? Config {path} not found. Using defaults.")
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def speak(self, text):
        print(f"??? {self.name}: {text}")
        try:
            engine = pyttsx3.init(driverName="sapi5")
            engine.setProperty("rate", self.config.get("agent", {}).get("rate", 180))
            engine.setProperty("volume", self.config.get("agent", {}).get("volume", 1.0))
            tts_voice_id = self.config.get("agent", {}).get("voice_id")
            if tts_voice_id:
                try:
                    engine.setProperty("voice", tts_voice_id)
                except Exception:
                    pass
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"? TTS error: {e}")

    def _get_whisper_model(self):
        """Lazy-load the Whisper model only when needed."""
        if self._whisper_model is None:
            try:
                from faster_whisper import WhisperModel
                print(f"? Loading Whisper model '{self.whisper_model_name}' (first-time download may take a moment)...")
                self._whisper_model = WhisperModel(self.whisper_model_name, compute_type="int8")
            except ImportError:
                print("? faster-whisper not installed. Run: pip install faster-whisper")
                return None
            except Exception as e:
                print(f"? Failed to load Whisper model: {e}")
                return None
        return self._whisper_model

    def _transcribe_whisper(self, audio):
        """Transcribe audio using local faster-whisper (offline)."""
        model = self._get_whisper_model()
        if model is None:
            return ""
        try:
            import numpy as np
            # Convert speech_recognition AudioData to numpy float32 array
            raw = audio.get_raw_data(convert_rate=16000, convert_width=2)
            samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            segments, _ = model.transcribe(samples, beam_size=5)
            try:
                text = " ".join(seg.text for seg in segments).strip()
            except KeyboardInterrupt:
                segments.close() if hasattr(segments, 'close') else None
                return ""
            return text.lower()
        except KeyboardInterrupt:
            return ""
        except Exception as e:
            print(f"? Whisper transcription error: {e}")
            return ""

    def _transcribe_google(self, audio):
        """Transcribe audio using Google Web Speech API (requires internet)."""
        try:
            return self.recognizer.recognize_google(audio).lower()
        except sr.UnknownValueError:
            print("? Could not understand audio.")
            return ""
        except sr.RequestError as e:
            print(f"? STT service error: {e}")
            return ""

    def listen(self, timeout=5, phrase_time_limit=7):
        if not self._mic_available:
            # Text input fallback when microphone is not available
            try:
                return input("You (type): ").strip().lower()
            except EOFError:
                return ""
        with suppress_c_stderr():
            with self.microphone as source:
                print("?? Listening...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                try:
                    audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                except sr.WaitTimeoutError:
                    print("?? Listening timed out.")
                    return ""

        if self.stt_provider == "whisper":
            text = self._transcribe_whisper(audio)
            # Fall back to Google if Whisper isn't available
            if not text:
                text = self._transcribe_google(audio)
        else:
            text = self._transcribe_google(audio)

        if text:
            print(f"?? You: {text}")
        return text

    def ask_llm(self, prompt):
        if self.llm_provider == "ollama":
            return self._ollama_chat(prompt)
        elif self.llm_provider == "openai":
            return self._openai_chat(prompt)
        elif self.llm_provider == "gemini":
            return self._gemini_chat(prompt)
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

    def _gemini_chat(self, prompt):
        import requests
        api_key = (
            self.config.get("llm", {}).get("gemini_api_key")
            or os.getenv("GEMINI_API_KEY")
        )
        if not api_key:
            return "Gemini API key not configured. Set GEMINI_API_KEY in .env or gemini_api_key in config.yaml."
        model = self.llm_model
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            data = {"contents": [{"parts": [{"text": prompt}]}]}
            resp = requests.post(url, json=data, timeout=60)
            if resp.status_code == 200:
                result = resp.json()
                candidates = result.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "No response from Gemini.")
                return "No response from Gemini."
            return f"Gemini error: {resp.status_code} {resp.text}"
        except Exception as e:
            return f"Gemini request failed: {e}"

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
        system = platform.system()
        try:
            if system == "Windows":
                return self._open_app_windows(app_name)
            elif system == "Darwin":
                return self._open_app_macos(app_name)
            else:  # Linux and others
                return self._open_app_linux(app_name)
        except Exception as e:
            return f"Failed to open {app_name}: {e}"

    def _open_app_windows(self, app_name):
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

    def _open_app_macos(self, app_name):
        mapping = {
            "notepad": "TextEdit",
            "calculator": "Calculator",
            "calc": "Calculator",
            "chrome": "Google Chrome",
            "browser": "Safari",
            "command prompt": "Terminal",
            "cmd": "Terminal",
            "task manager": "Activity Monitor",
        }
        for key, app in mapping.items():
            if key in app_name:
                subprocess.Popen(["open", "-a", app])
                return f"Opening {app}."
        return f"Sorry, I don't know how to open {app_name}."

    def _open_app_linux(self, app_name):
        mapping = {
            "notepad": ["gedit", "mousepad", "leafpad", "nano", "vim"],
            "calculator": ["gnome-calculator", "kcalc", "qalculate-gtk"],
            "calc": ["gnome-calculator", "kcalc", "qalculate-gtk"],
            "chrome": ["google-chrome", "chromium-browser", "chromium", "firefox"],
            "browser": ["google-chrome", "chromium-browser", "chromium", "firefox"],
            "command prompt": ["gnome-terminal", "konsole", "xterm", "terminator"],
            "cmd": ["gnome-terminal", "konsole", "xterm", "terminator"],
            "task manager": ["gnome-system-monitor", "ksystemguard", "htop"],
        }
        for key, candidates in mapping.items():
            if key in app_name:
                for cmd in candidates:
                    try:
                        subprocess.Popen([cmd])
                        return f"Opening {cmd}."
                    except FileNotFoundError:
                        continue
                return f"Sorry, I couldn't find a suitable app for {app_name}."
        return f"Sorry, I don't know how to open {app_name}."

    def open_website(self, site):
        site = site.lower().strip()
        # Jo bola jayega: agar pehle se .com/domain nahi hai toh .com jod dein taaki clean sune
        if "." not in site:
            display_site = site + ".com"
        else:
            display_site = site
        if not site.startswith("http"):
            if "." in site:
                url = "https://www." + site
            else:
                url = "https://www." + site + ".com"
        else:
            url = site
        webbrowser.open(url)
        return f"Opening {display_site}"

    # ------------------------------------------------------------------
    # Installed apps survey (PC-wide) — so any app name works by voice
    # ------------------------------------------------------------------
    def _scan_installed_apps(self):
        app_map = {}
        for pattern in [
            os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\**\*.lnk"),
            os.path.expandvars(r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs\**\*.lnk"),
        ]:
            try:
                for lnk in glob.glob(pattern, recursive=True):
                    name = os.path.splitext(os.path.basename(lnk))[0].lower()
                    if name:
                        app_map.setdefault(name, lnk)
            except Exception:
                continue
        for hive, subkey in [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]:
            try:
                with winreg.OpenKey(hive, subkey) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            sub = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, sub) as k:
                                try:
                                    dname = winreg.QueryValueEx(k, "DisplayName")[0]
                                except FileNotFoundError:
                                    continue
                                if not dname:
                                    continue
                                name = dname.lower()
                                if name in app_map:
                                    continue
                                path = None
                                try:
                                    loc = winreg.QueryValueEx(k, "InstallLocation")[0]
                                    if loc and os.path.exists(loc):
                                        path = loc
                                except FileNotFoundError:
                                    pass
                                if not path:
                                    try:
                                        ico = winreg.QueryValueEx(k, "DisplayIcon")[0]
                                        p = ico.split(",")[0].strip().strip('"')
                                        if os.path.exists(p):
                                            path = p
                                    except FileNotFoundError:
                                        pass
                                if path:
                                    # Skip driver / component GUID folders — not user-launchable apps
                                    if "{" in path and "}" in path:
                                        continue
                                    skip_keywords = [
                                        "driver", "update", "redistributable",
                                        "c++", ".net", "visual c++", "runtime",
                                        "setup", "installer", "uninstall",
                                    ]
                                    if any(k in name for k in skip_keywords):
                                        continue
                                    app_map[name] = path
                                    app_map[name.replace(" ", "")] = path
                        except Exception:
                            continue
            except Exception:
                continue
        return app_map

    def find_app(self, name):
        name = name.lower().strip()
        if not name:
            return None
        # 1) Exact match
        if name in self.app_map:
            return self.app_map[name]
        # 2) Whole-word match: every word of command present in app name
        words = name.split()
        for app_name, path in self.app_map.items():
            if "{" in path and "}" in path:
                continue  # skip GUID driver folders
            if all(w in app_name for w in words) or app_name in name:
                return path
        # 3) Loose substring match (last resort), still skip GUIDs
        for app_name, path in self.app_map.items():
            if "{" in path and "}" in path:
                continue
            if app_name in name or name in app_name:
                return path
        return None

    def open_app_path(self, path):
        try:
            if os.path.isdir(path):
                os.startfile(path)
                return f"Opening {os.path.basename(path) or path}."
            os.startfile(path)
            return f"Opening {os.path.basename(path)}."
        except Exception as e:
            return f"Failed to open app: {e}"

    def _user_folder(self, folder):
        return os.path.expandvars(f"%USERPROFILE%\\{folder}")

    def open_file_from_location(self, location, filename):
        folder = self._user_folder("Desktop" if location == "desktop" else "Downloads")
        filepath = os.path.join(folder, filename)
        if not os.path.exists(filepath):
            for ext in [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".pptx", ".jpg", ".png", ".zip", ".mp4", ".mp3"]:
                if os.path.exists(filepath + ext):
                    filepath = filepath + ext
                    break
            else:
                return f"Sorry, I couldn't find {filename} in {location}."
        try:
            os.startfile(filepath)
            return f"Opening {filename} from {location}."
        except Exception as e:
            return f"Failed to open file: {e}"

    def open_latest_downloads(self):
        folder = self._user_folder("Downloads")
        if not os.path.isdir(folder):
            return "Downloads folder not found."
        files = [
            os.path.join(folder, f)
            for f in os.listdir(folder)
            if os.path.isfile(os.path.join(folder, f))
        ]
        if not files:
            return "Downloads folder is empty."
        latest = max(files, key=os.path.getmtime)
        try:
            os.startfile(latest)
            return f"Opening latest file: {os.path.basename(latest)}."
        except Exception as e:
            return f"Failed to open latest file: {e}"

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
        wake_token = None
        if self.wake_enabled:
            if self.wake_phrase in text:
                wake_token = self.wake_phrase
            elif self.name.lower() in text:
                # STT often drops the "hey" — accept the agent name alone
                wake_token = self.name.lower()
        else:
            # Wake word disabled — process command directly
            wake_token = ""
        if wake_token is None:
            wake_token = ""
        command = text.replace(wake_token, "", 1).strip()
        if not command:
            return f"Yes, I am listening. How can I help you?"
        if "open" in command:
            cmd = command.replace("open", "", 1).strip()

            # 1) File from Desktop / Downloads / latest downloads
            if "from desktop" in cmd:
                target = cmd.replace("from desktop", "").strip()
                if target:
                    return self.open_file_from_location("desktop", target)
                return "Please specify the file name."
            if "from downloads" in cmd:
                target = cmd.replace("from downloads", "").strip()
                if "latest" in target:
                    return self.open_latest_downloads()
                if target:
                    return self.open_file_from_location("downloads", target)
                return "Please specify the file name."
            if "latest file from downloads" in cmd or "latest download" in cmd:
                return self.open_latest_downloads()

            # 2) Installed app (from PC survey — any app name works)
            app_path = self.find_app(cmd)
            if app_path:
                return self.open_app_path(app_path)

            # 3) Hardcoded fallback apps
            for app in ["notepad", "calculator", "calc", "chrome", "browser", "command prompt", "cmd", "task manager"]:
                if app in cmd:
                    return self.open_app(cmd.replace(app, "").strip() or app)

            # 4) Website fallback: "open flipkart", "open nvidia", etc.
            fillers = {"website", "site", "the", "a", "an", "please"}
            site = " ".join(w for w in cmd.split() if w.lower() not in fillers).strip()
            if site:
                return self.open_website(site)
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
