"""
Unified AI provider client - supports OpenAI, Google Gemini, and Ollama API Gateway.
Handles chat completions, embedding generation, summary generation, streaming, and vision.
"""

import os
import json
import logging
import httpx
from openai import AsyncOpenAI
import google.generativeai as genai
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Fallback for new API Key if not in settings class
OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY", "sk-local-dev123")

class AIClient:
    def __init__(self):
        self._openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        if settings.GOOGLE_API_KEY:
            genai.configure(api_key=settings.GOOGLE_API_KEY)
        self._ollama_base_url = settings.OLLAMA_BASE_URL.rstrip('/') # URL এর শেষে স্পেস বা / থাকলে মুছে দেবে
        self._http_client = httpx.AsyncClient(timeout=120.0)

    async def chat(self, provider_type: str, model_name: str, system_prompt: str, messages: list[dict], config: dict = None) -> str:
        config = config or {}
        if provider_type == "openai":
            return await self._openai_chat(model_name, system_prompt, messages, config)
        elif provider_type == "google":
            return await self._google_chat(model_name, system_prompt, messages, config)
        elif provider_type == "ollama":
            return await self._ollama_chat(model_name, system_prompt, messages, config)
        else:
            raise ValueError(f"Unsupported provider: {provider_type}")

    # =========================================================================
    # 🚀 LAISA'S UPGRADE: TRUE STREAMING GENERATOR FOR ALL PROVIDERS
    # =========================================================================
    async def stream_chat_generator(self, provider_type: str, model: str, system_prompt: str, messages: list[dict], config: dict):
        try:
            # 🟢 1. OPENAI TRUE STREAMING
            if provider_type == "openai":
                openai_messages = [{"role": "system", "content": system_prompt}] + messages
                stream = await self._openai_client.chat.completions.create(
                    model=model, 
                    messages=openai_messages, 
                    temperature=config.get("temperature", 0.7),
                    stream=True
                )
                async for chunk in stream:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield f"data: {json.dumps({'content': content})}\n\n"
                yield "data: [DONE]\n\n"

            # 🔵 2. GOOGLE GEMINI TRUE STREAMING
            elif provider_type == "google":
                gemini_model = genai.GenerativeModel(model_name=model, system_instruction=system_prompt)
                gemini_history = [{"role": "user" if msg["role"] == "user" else "model", "parts": [msg["content"]]} for msg in messages[:-1]]
                chat = gemini_model.start_chat(history=gemini_history)
                last_message = messages[-1]["content"] if messages else ""

                response = await chat.send_message_async(last_message, stream=True) 
                async for chunk in response:
                    if chunk.text:
                        yield f"data: {json.dumps({'content': chunk.text})}\n\n"
                yield "data: [DONE]\n\n"

            # 🟠 3. NEW OLLAMA API GATEWAY STREAMING (Updated Endpoint & Headers)
            elif provider_type == "ollama":
                ollama_messages = [{"role": "system", "content": system_prompt}] + messages
                
                # Payload updated according to new openapi.json (temperature is root level now)
                payload = {
                    "model": model,
                    "messages": ollama_messages,
                    "stream": True,
                    "temperature": config.get("temperature", 0.7),
                    "keep_alive": -1
                }
                
                # Dynamic API Key from Database config or environment fallback
                headers = {
                    "X-API-Key": config.get("api_key", OLLAMA_API_KEY),
                    "Content-Type": "application/json"
                }

                # Endpoint updated to /api/v1/chat/stream
                async with self._http_client.stream("POST", f"{self._ollama_base_url}/api/v1/chat/stream", json=payload, headers=headers) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line: continue
                        
                        # API Gateway returns SSE (Server-Sent Events) starting with 'data: '
                        if line.startswith("data: "):
                            line = line[6:]
                            
                        if line.strip() == "[DONE]":
                            break
                            
                        try:
                            data = json.loads(line)
                            content = ""
                            # Supports both raw Ollama style and OpenAI-compatible style chunks
                            if "message" in data and "content" in data["message"]:
                                content = data["message"]["content"]
                            elif "choices" in data and len(data["choices"]) > 0 and "delta" in data["choices"][0]:
                                content = data["choices"][0]["delta"].get("content", "")
                                
                            if content:
                                yield f"data: {json.dumps({'content': content})}\n\n"
                        except json.JSONDecodeError:
                            continue
                            
                yield "data: [DONE]\n\n"

            else:
                raise ValueError(f"Unsupported provider for streaming: {provider_type}")

        except Exception as e:
            logger.error(f"Streaming error for {provider_type}: {e}")
            err_msg = f" \n\n[System Network Error: Trying to reconnect... Details: {str(e)[:50]}]"
            yield f"data: {json.dumps({'content': err_msg})}\n\n"
            yield "data: [DONE]\n\n"

    # --- Other Methods ---
    async def _openai_chat(self, model: str, system_prompt: str, messages: list[dict], config: dict) -> str:
        openai_messages = [{"role": "system", "content": system_prompt}]
        openai_messages.extend(messages)
        response = await self._openai_client.chat.completions.create(
            model=model, messages=openai_messages, temperature=config.get("temperature", 0.7), max_tokens=config.get("max_tokens", 1024),
        )
        return response.choices[0].message.content

    async def _google_chat(self, model: str, system_prompt: str, messages: list[dict], config: dict) -> str:
        gemini_model = genai.GenerativeModel(model_name=model, system_instruction=system_prompt)
        gemini_history = [{"role": "user" if msg["role"] == "user" else "model", "parts": [msg["content"]]} for msg in messages[:-1]]
        chat = gemini_model.start_chat(history=gemini_history)
        last_message = messages[-1]["content"] if messages else ""
        response = await chat.send_message_async(last_message)
        return response.text

    # 🚀 FIX: Non-streaming Ollama Gateway Chat
    async def _ollama_chat(self, model: str, system_prompt: str, messages: list[dict], config: dict) -> str:
        ollama_messages = [{"role": "system", "content": system_prompt}]
        ollama_messages.extend(messages)
        payload = {
            "model": model, 
            "messages": ollama_messages, 
            "stream": False, 
            "temperature": config.get("temperature", 0.7), 
            "num_predict": config.get("max_tokens", 1024),
            "keep_alive": -1
        }
        headers = {"X-API-Key": config.get("api_key", OLLAMA_API_KEY)}
        
        try:
            response = await self._http_client.post(f"{self._ollama_base_url}/api/v1/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            # Robust parsing for both formats
            if "choices" in data:
                return data["choices"][0]["message"]["content"]
            elif "message" in data:
                return data["message"]["content"]
            else:
                return str(data)
                
        except httpx.HTTPError as e:
            logger.error(f"Ollama chat error: {e}")
            raise ValueError(f"Ollama API error: {str(e)}")

    # 🚀 FIX: Gateway Vision Model Implementation
    async def analyze_receipt_image(self, base64_image: str, model_name: str = "qwen2.5vl:latest") -> str:
        clean_base64 = base64_image.split(",")[-1] if "," in base64_image else base64_image
        prompt = """You are a financial verifier AI for ICT Bangladesh. Analyze this payment screenshot and extract: Transaction ID, Amount, Payment Method, and confirm if it looks valid."""
        
        # New Gateway Vision format from openapi.json
        payload = {
            "model": model_name,
            "prompt": prompt,
            "images": [clean_base64], 
            "stream": False,
            "temperature": 0.1
        }
        headers = {"X-API-Key": OLLAMA_API_KEY}
        
        try:
            # Endpoint updated to /api/v1/vision/chat
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(f"{self._ollama_base_url}/api/v1/vision/chat", json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                if "choices" in data: return data["choices"][0]["message"]["content"]
                return data.get("message", {}).get("content", str(data))
                
        except Exception as e:
            logger.error(f"Vision analysis failed for model {model_name}: {e}")
            return "[SYSTEM: The image was received but vision processing timed out or failed on the local server. Please verify the receipt manually from the admin panel.]"

    # 🚀 FIX: Gateway Embeddings Endpoint
    async def generate_embedding(self, text: str) -> list[float]:
        if self._openai_client: 
            return await self._openai_embedding(text)
        elif settings.GOOGLE_API_KEY:
            result = genai.embed_content(model="models/text-embedding-004", content=text)
            return result['embedding']
        else: 
            return await self._ollama_embedding(text)

    async def _openai_embedding(self, text: str) -> list[float]:
        response = await self._openai_client.embeddings.create(model=settings.EMBEDDING_MODEL, input=text)
        return response.data[0].embedding

    async def _ollama_embedding(self, text: str) -> list[float]:
        # New Embedding payload format
        payload = {"model": settings.OLLAMA_EMBEDDING_MODEL, "prompt": text, "keep_alive": -1}
        headers = {"X-API-Key": OLLAMA_API_KEY}
        
        try:
            # Endpoint updated to /api/v1/embeddings
            response = await self._http_client.post(f"{self._ollama_base_url}/api/v1/embeddings", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if "embedding" in data: 
                return data["embedding"]
            elif "embeddings" in data and len(data["embeddings"]) > 0: 
                return data["embeddings"][0]
            else: 
                raise ValueError("No embedding data found.")
        except httpx.HTTPError as e:
            logger.error(f"Ollama embedding error: {e}")
            raise ValueError(f"Ollama embedding error: {str(e)}")

    # 🚀 FIX: Redirecting Summary generation to Chat Completions
    async def generate_summary(self, entity_type: str, data: dict) -> str:
        prompt = f"Summarize the following {entity_type} data into a clear, concise, natural language description.\nData:\n{json.dumps(data, indent=2, default=str)}\nWrite a comprehensive summary in 2-3 sentences:"
        
        if self._openai_client:
            response = await self._openai_client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], temperature=0.3, max_tokens=300)
            return response.choices[0].message.content
        elif settings.GOOGLE_API_KEY: 
            gemini_model = genai.GenerativeModel(model_name="gemini-1.5-flash")
            response = await gemini_model.generate_content_async(prompt)
            return response.text
        else:
            return await self._ollama_generate(prompt)

    async def _ollama_generate(self, prompt: str, model: str = None) -> str:
        # Gateway doesn't have /api/generate, so we use /api/v1/chat/completions instead
        payload = {
            "model": model or "llama3.1:latest", 
            "messages": [{"role": "user", "content": prompt}], 
            "stream": False, 
            "temperature": 0.3, 
            "num_predict": 300,
            "keep_alive": -1
        }
        headers = {"X-API-Key": OLLAMA_API_KEY}
        
        try:
            response = await self._http_client.post(f"{self._ollama_base_url}/api/v1/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            if "choices" in data: return data["choices"][0]["message"]["content"]
            return data.get("message", {}).get("content", str(data))
        except httpx.HTTPError as e:
            logger.error(f"Ollama generate error: {e}")
            return f"{prompt.split('Data:')[0].strip()}"

    async def close(self):
        await self._http_client.aclose()

ai_client = AIClient()
