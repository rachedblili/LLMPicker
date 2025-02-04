from llama_index.llms import openai, anthropic,gemini, groq, openai_like, bedrock_converse
from typing import List
import time
from config import get_config
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
gemini_api_key = os.getenv("GEMINI_API_KEY")
groq_api_key = os.getenv("GROQ_API_KEY")
sambanova_api_key = os.getenv("SAMBANOVA_API_KEY")
aws_access_key = os.getenv("AWS_ACCESS_KEY")
aws_access_secret = os.getenv("AWS_ACCESS_SECRET")
deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
qwen_api_key = os.getenv("QWEN_API_KEY")

client_functions = {
    "choose" : None,
    "openai": lambda model: openai.OpenAI(api_key=openai_api_key, model=model, max_tokens=4096),
    "anthropic": lambda model: anthropic.Anthropic(api_key=anthropic_api_key, model=model, max_tokens=4096),
    "gemini": lambda model: gemini.Gemini(api_key=gemini_api_key, model=model, max_tokens=4096),
    "groq": lambda model: groq.Groq(api_key=groq_api_key, model=model, max_tokens=4096),
    "aws": lambda model: bedrock_converse.BedrockConverse(aws_access_key_id=aws_access_key,
                                                          aws_secret_access_key=aws_access_secret,
                                                          region_name="us-east-1",model=model, max_tokens=4096),
    "sambanova": lambda model: openai_like.OpenAILike(api_base="https://api.sambanova.ai/v1/",
                                                      api_key=sambanova_api_key, model=model, max_tokens=2048),
    "deepseek": lambda model: openai_like.OpenAILike(api_base="https://api.deepseek.com", is_chat_model=True,
                                                    api_key=deepseek_api_key, model=model, max_tokens=4096),
    "alibaba": lambda model: openai_like.OpenAILike(api_base="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
                                                    is_chat_model=True, api_key=qwen_api_key, model=model,
                                                    max_tokens=4096)

}


def list_providers() -> List[str]:
    return list(client_functions.keys())


def list_models(provider: str) -> List[str]:
    models = get_config()["llm_providers"][provider]["models"]
    return models
