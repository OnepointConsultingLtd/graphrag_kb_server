from google import genai
from google.genai import types
import jiter
from openai import AsyncOpenAI
from openrouter import OpenRouter

from pydantic import BaseModel

from graphrag_kb_server.config import cfg, lightrag_cfg


async def structured_completion(
    system_message: str,
    user_message: str,
    response_schema: BaseModel,
    model: str = lightrag_cfg.lightrag_model,
) -> dict:

    client = genai.Client(api_key=cfg.gemini_api_key)
    contents = f"""
system: {system_message}
user:{user_message}
"""
    match model:
        case model if model.startswith("gemini"):
            response = await client.aio.models.generate_content(
                model=model,
                contents=[contents],
                config=types.GenerateContentConfig(
                    response_schema=response_schema,
                    response_mime_type="application/json",
                ),
            )
            return jiter.from_json(response.text.encode(encoding="utf-8"))
        case model if model.startswith("gpt"):
            client = AsyncOpenAI()
            response = await client.beta.chat.completions.parse(
                model=model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message},
                ],
                response_format=response_schema,
            )
            return jiter.from_json(
                response.choices[0].message.content.encode(encoding="utf-8")
            )
        case _:
            # Use OpenRouter as default
            schema_dict = response_schema.model_json_schema()
            schema_name = schema_dict.get("title", response_schema.__name__)

            async with OpenRouter(api_key=cfg.openrouter_api_key) as client:
                config_dict = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": user_message},
                    ],
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": schema_name,
                            "schema": schema_dict,
                            "strict": True,
                        },
                    },
                }
                # Add provider parameter if specified in config
                if cfg.openrouter_provider:
                    config_dict["provider"] = {"name": cfg.openrouter_provider}

                response = await client.chat.send_async(**config_dict)
                return jiter.from_json(
                    response.choices[0].message.content.encode(encoding="utf-8")
                )
