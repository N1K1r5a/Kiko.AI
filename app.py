import os
from flask import Flask, render_template, request, jsonify
import json
import urllib.request
import urllib.error

app = Flask(__name__)

OLLAMA_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://127.0.0.1:11434/api/chat"
)

MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")

SYSTEM_PROMPT = """
You are Kiko, a friendly and thoughtful AI assistant.
You speak naturally, warmly, and clearly.
Your personality is gentle, curious, helpful, and encouraging.
You can use an occasional purple heart emoji.
Be honest when you don't know something.
"""


@app.route("/")
def home():
    return render_template("index.html")


from datetime import datetime

def get_time_date_reply(message):
    text = message.lower()

    time_words = ["time", "clock", "what time"]
    date_words = ["date", "what day", "today", "day is it"]

    asks_time = any(word in text for word in time_words)
    asks_date = any(word in text for word in date_words)

    now = datetime.now()

    if asks_time and asks_date:
        return (
            "It's " + now.strftime("%I:%M %p").lstrip("0")
            + " on " + now.strftime("%A %d %B %Y") + ". 💜"
        )

    if asks_time:
        return "It's " + now.strftime("%I:%M %p").lstrip("0") + ". 💜"

    if asks_date:
        return "Today is " + now.strftime("%A %d %B %Y") + ". 💜"

    return None

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    messages = data.get("messages", [])

    if not isinstance(messages, list) or not messages:
        return jsonify({"error": "Please enter a message."}), 400

    # Accept only recent user and assistant messages.
    safe_messages = []

    for item in messages[-20:]:
        if not isinstance(item, dict):
            continue

        role = item.get("role")
        content = item.get("content")

        if role not in ("user", "assistant"):
            continue

        if not isinstance(content, str):
            continue

        content = content.strip()

        if content and len(content) <= 2000:
            safe_messages.append({
                "role": role,
                "content": content
            })

    if not safe_messages or safe_messages[-1]["role"] != "user":
        return jsonify({"error": "Please send a valid message."}), 400

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            *safe_messages
        ],
        "stream": False
    }

    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
    "Content-Type": "application/json",
    **(
        {"Authorization": f"Bearer {os.environ['OLLAMA_API_KEY']}"}
        if os.getenv("OLLAMA_API_KEY")
        else {}
    )
},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            result = json.loads(response.read().decode("utf-8"))

        reply = result.get("message", {}).get("content", "").strip()

        if not reply:
            return jsonify({"error": "Kiko returned an empty reply."}), 502

        return jsonify({"reply": reply})

    except urllib.error.URLError:
        app.logger.exception("Could not connect to Ollama")
        return jsonify({
            "error": "I can't reach Ollama. Please check that Ollama is running."
        }), 503

    except (TimeoutError, json.JSONDecodeError):
        return jsonify({
            "error": "Kiko took too long to respond. Please try again."
        }), 504


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
