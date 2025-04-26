from g4f.client import Client
from flask import Flask, request, jsonify, send_file
from g4f.Provider import HarProvider, PollinationsAI
import asyncio
from functools import wraps
import os

app = Flask(__name__)
client = Client()

MODEL_MAPPING = {
    "botintel-v3": "chatgpt-4o-latest-20250326",
    "botintel-pro": "o3-2025-04-16",
    "botintel-coder": "claude-3-7-sonnet-20250219-thinking-32k",
    "abuai-v3-latest": "chatgpt-4o-latest-20250326"
}

PROVIDER_MAPPING = {
    "botintel-v3": HarProvider,
    "botintel-pro": HarProvider,
    "botintel-coder": HarProvider,
    "abuai-v3-latest": HarProvider
}

def async_to_sync(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(f(*args, **kwargs))
        finally:
            loop.close()
    return wrapper

def process_messages(messages):
    return [msg for msg in messages if msg.get("role") != "system"]

@app.route("/v1/models", methods=["GET"])
def get_models():
    model_json_path = os.path.join(os.path.dirname(__file__), "models.json")
    return send_file(model_json_path, mimetype="application/json")

@app.route("/v1/chat/completions", methods=["POST"])
@async_to_sync
async def chat_completions():
    data = request.get_json()
    frontend_model = data.get("model", "botintel-v3")
    original_messages = data.get("messages", [])
    
    messages = process_messages(original_messages)
    backend_model = MODEL_MAPPING.get(frontend_model, "chatgpt-4o-latest-20250326")
    provider = PROVIDER_MAPPING.get(frontend_model, HarProvider)

    try:
        response = await client.chat.completions.create(
            model=backend_model,
            messages=messages,
            web_search=False,
            provider=provider,
        )

        return jsonify({
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 0,
            "model": frontend_model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response.choices[0].message.content
                },
                "finish_reason": "stop"
            }]
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "message": "An error occurred while processing your request"
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
