from g4f.client import Client
from flask import Flask, request, jsonify, Response
from g4f.Provider import HarProvider
import json
import time

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

def process_messages(messages):
    return [msg for msg in messages if msg['role'] not in ['system']]

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    data = request.get_json()
    messages = data.get('messages', [])
    model_name = data.get('model', 'botintel-v3')
    stream = data.get('stream', False)

    processed_messages = process_messages(messages)
    backend_model = MODEL_MAPPING.get(model_name, "chatgpt-4o-latest-20250326")
    provider = PROVIDER_MAPPING.get(model_name, HarProvider)

    try:
        if stream:
            def generate():
                full_response = []
                response = client.chat.completions.create(
                    model=backend_model,
                    messages=processed_messages,
                    provider=provider,
                    stream=True
                )
                
                for chunk in response:
                    content = chunk.choices[0].delta.content
                    if content:
                        full_response.append(content)
                        data = json.dumps({
                            'id': f'chatcmpl-{int(time.time())}',
                            'object': 'chat.completion.chunk',
                            'created': int(time.time()),
                            'model': model_name,
                            'choices': [{
                                'delta': {'content': content},
                                'index': 0,
                                'finish_reason': None
                            }]
                        })
                        yield f"data: {data}\n\n"
                
                # Send final completion event
                data = json.dumps({
                    'id': f'chatcmpl-{int(time.time())}',
                    'object': 'chat.completion.chunk',
                    'created': int(time.time()),
                    'model': model_name,
                    'choices': [{
                        'delta': {},
                        'index': 0,
                        'finish_reason': 'stop'
                    }]
                })
                yield f"data: {data}\n\n"
                yield "data: [DONE]\n\n"

            return Response(generate(), mimetype='text/event-stream')

        else:
            response = client.chat.completions.create(
                model=backend_model,
                messages=processed_messages,
                provider=provider
            )

            return jsonify({
                'id': f'chatcmpl-{int(time.time())}',
                'object': 'chat.completion',
                'created': int(time.time()),
                'model': model_name,
                'choices': [{
                    'message': {
                        'role': 'assistant',
                        'content': response.choices[0].message.content
                    },
                    'finish_reason': 'stop',
                    'index': 0
                }]
            })

    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': 'Error processing request'
        }), 500

@app.route('/v1/models', methods=['GET'])
def get_models():
    return jsonify({
        "data": [
            {"id": "botintel-v3", "object": "model"},
            {"id": "botintel-pro", "object": "model"},
            {"id": "botintel-coder", "object": "model"},
            {"id": "abuai-v3-latest", "object": "model"}
        ]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
