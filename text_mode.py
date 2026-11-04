"""
Text-based interaction mode for Diablo (JarvisAgent).
Runs the same agent logic but reads commands from stdin instead of a microphone,
so it works in headless environments without audio hardware.
"""
import sys
import os

# Make the repo importable
REPO_DIR = os.path.dirname(os.path.abspath(__file__))
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

# Stub pyautogui so imports succeed without an X display
STUBS_DIR = "/tmp/opencode/stubs"
if STUBS_DIR not in sys.path:
    sys.path.insert(0, STUBS_DIR)
os.environ.setdefault("DISPLAY", ":99")

from main import JarvisAgent


def main():
    agent = JarvisAgent()
    print(f"\n{agent.name} is ready (text mode). Type your commands below.")
    print('Say "hey diablo" followed by your command, e.g. "hey diablo what is the time"')
    print("Type 'exit' or 'quit' to stop.\n")

    while True:
        try:
            text = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not text:
            continue
        if any(w in text.lower() for w in ["exit", "quit", "stop", "goodbye"]):
            agent.speak("Goodbye! Have a great day.")
            break

        response = agent.handle_command(text)
        if response:
            print(f"{agent.name}: {response}")


if __name__ == "__main__":
    main()
