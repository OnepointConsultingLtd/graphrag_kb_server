import json

from google import genai
from google.genai import types

from pydantic import BaseModel

from graphrag_kb_server.config import cfg, lightrag_cfg

async def structured_completion(system_message: str, user_message: str, response_schema: BaseModel) -> dict:
    client = genai.Client(api_key=cfg.gemini_api_key)
    contents = f"""
system: {system_message}
user:{user_message}
"""
    response = await client.aio.models.generate_content(
        model=lightrag_cfg.lightrag_model,
        contents=[contents],
        config=types.GenerateContentConfig(
            response_schema=response_schema, response_mime_type="application/json"
        ),
    )
    return json.loads(response.text)