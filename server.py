from flask import Flask, request, jsonify
from flask_cors import CORS
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.chat_engine import SimpleChatEngine
from llama_index.core.text_splitter import TokenTextSplitter
from llama_index.core.types import ChatMessage, MessageRole
import llms
from flask_shield import FlaskShield


app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize with tokens and allowed IPs
shield = FlaskShield(
    app,
    allowed_ips=['107.174.92.131/32','67.169.42.77/32'],
    trust_proxy=True,
    require_token=False
)

# Store active LLM clients
active_clients = {}

def create_chat_engine_from_client(llm):
    memory = ChatMemoryBuffer.from_defaults(token_limit=65536)
    chat_engine = SimpleChatEngine.from_defaults(
        llm=llm,
        memory=memory
    )
    return chat_engine,memory

@app.route('/api/providers', methods=['GET'])
def get_providers():
    providers = llms.list_providers()
    print("Got providers: ",providers)
    return jsonify({"providers": providers})

@app.route('/api/models/<provider>', methods=['GET'])
def get_models(provider):
    print("Looking up models for: ",provider)
    try:
        models = llms.list_models(provider)
        return jsonify({"models": models})
    except KeyError:
        return jsonify({"error": f"Provider {provider} not found"}), 404

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    if not data or 'message' not in data or 'provider' not in data or 'model' not in data:
        return jsonify({"error": "Missing required fields"}), 400

    provider = data['provider']
    model = data['model']
    message = data['message']
    
    try:
        # Create client if not exists
        client_key = f"{provider}_{model}"
        if client_key not in active_clients:
            client_fn = llms.client_functions[provider]
            chat_engine,memory = create_chat_engine_from_client(client_fn(model))
            active_clients[client_key] = {"client": chat_engine, "memory": memory}  # Store the chat_engine
        
        # Get response from LLM
        client = active_clients[client_key]["client"]
        memory = active_clients[client_key]["memory"]
        text_splitter = TokenTextSplitter(chunk_size=2048, chunk_overlap=0)
        chunks = text_splitter.split_text(message)
        # Loop through all but the last chunk
        for chunk in chunks[:-1]:
            memory.put(ChatMessage(role=MessageRole.USER, content=chunk))
        chat_history = memory.get()

        response = client.chat(chunks[-1], chat_history=chat_history)

        return jsonify({
            "role": "assistant",
            "content": str(response)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5555)

