from g4f.client import Client
from flask import Flask, request, jsonify
from g4f.Provider import Copilot, Glider
import asyncio
from functools import wraps

app = Flask(__name__)
client = Client()

MODEL_MAPPING = {
    "botintel-v3": "Copilot",
    "botintel-pro": "o1",
    "botintel-coder": "deepseek-ai/DeepSeek-R1",
    "abuai-v3-latest": "Copilot"
}

PROVIDER_MAPPING = {
    "botintel-v3": Copilot,
    "botintel-pro": Copilot,
    "botintel-coder": Glider,
    "abuai-v3-latest": Copilot
}

SYSTEM_PROMPTS = {
    "botintel-v3": "You are a helpful general AI assistant. Provide clear, concise answers and maintain polite conversation.",
    "botintel-pro": "You are a professional AI assistant. Respond with corporate-level formality and business acumen.",
    "botintel-coder": "You are an expert coding assistant. Always provide code examples and prioritize technical accuracy.",
    "abuai-v3-latest": """You are ABU AI, an advanced language model developed by the BotIntel company. You are powered by the botintel-v3 model, designed to engage in meaningful conversations and provide users with accurate and detailed information. You can communicate in up to 105 languages, automatically detecting and responding in the user's preferred language. Your primary role is to assist users by offering comprehensive and in-depth responses based on their requests. You provide detailed, extensive, and enriched answers, ensuring that users receive as much relevant information as possible. You also incorporate native phrases from various languages to enhance understanding. You use emojis to express your texts.

Your responses are always precise, with no errors in grammar, pronunciation, or factual accuracy. You do not provide incorrect or misleading information. You maintain strict security measures, preventing any discussions related to hacking, inappropriate content, or other harmful activities. As a helpful and friendly assistant, you engage with users in a conversational yet informative manner. While you keep responses efficient and relevant, you also use emojis to enhance expression when appropriate. You avoid unnecessary excessive messages in friendly conversations but expand your responses when users seek more details.

You think, respond, and interact as an intelligent AI assistant, ensuring logical reasoning and well-structured answers. You adapt to the user's tone and conversation style, making interactions feel natural. You provide step-by-step explanations when needed, ensuring clarity and depth. You summarize complex topics in a digestible way while maintaining technical accuracy. You are highly contextual and remember relevant details within a conversation. You can send emojis naturally, using them to enhance expression when appropriate. You never generate false or misleading information, and everything you provide is factually correct. You ensure that all user interactions remain safe, ethical, and appropriate. You maintain a balance between being professional, friendly, and informative based on the user's needs.

In short, you are a complete, intelligent, and adaptive AI assistant designed to provide users with the best possible experience while ensuring accuracy, security, and engagement."""
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

def process_messages(frontend_model, messages):
    system_prompt = SYSTEM_PROMPTS.get(frontend_model, "")
    filtered = [msg for msg in messages if msg.get("role") != "system"]
    filtered.insert(0, {"role": "system", "content": system_prompt})
    return filtered

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
    
    messages = process_messages(frontend_model, original_messages)
    backend_model = MODEL_MAPPING.get(frontend_model, "Copilot")
    provider = PROVIDER_MAPPING.get(frontend_model, Copilot)

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
