import asyncio
from google import genai
from google.genai import types
from google.genai.errors import APIError as GenaiAPIError
import jiter
from openai import (
    AsyncOpenAI,
    AuthenticationError as OpenAIAuthError,
    BadRequestError as OpenAIBadRequestError,
    NotFoundError as OpenAINotFoundError,
    PermissionDeniedError as OpenAIPermissionDeniedError,
    UnprocessableEntityError as OpenAIUnprocessableEntityError,
)
from openrouter import OpenRouter
from openrouter.errors import (
    UnauthorizedResponseError,
    ForbiddenResponseError,
    BadRequestResponseError,
    NotFoundResponseError,
    PaymentRequiredResponseError,
    UnprocessableEntityResponseError as ORUnprocessableEntityError,
)

from pydantic import BaseModel

from graphrag_kb_server.logger import logger
from graphrag_kb_server.service.project_config_service import ProjectConfig

_NON_RETRYABLE_ERRORS = (
    OpenAIAuthError,
    OpenAIBadRequestError,
    OpenAINotFoundError,
    OpenAIPermissionDeniedError,
    OpenAIUnprocessableEntityError,
    UnauthorizedResponseError,
    ForbiddenResponseError,
    BadRequestResponseError,
    NotFoundResponseError,
    PaymentRequiredResponseError,
    ORUnprocessableEntityError,
    TypeError,
    KeyError,
)

MAX_RETRIES = 5
_RAW_OUTPUT_LOG_LIMIT = 2000


def _is_retryable(error: Exception) -> bool:
    if isinstance(error, _NON_RETRYABLE_ERRORS):
        return False
    if isinstance(error, ValueError):
        return True
    if isinstance(error, GenaiAPIError) and error.code is not None:
        return error.code >= 429 or error.code in (408, 409)
    return True


async def structured_completion(
    system_message: str,
    user_message: str,
    response_schema: BaseModel,
    *,
    config: ProjectConfig,
    model: str | None = None,
) -> dict:
    """Run a prompt and return the JSON answer matching the schema.

    The API keys come from the project configuration. The model defaults to the project's
    LightRAG model; the provider is chosen from the model name (gemini*, gpt*, otherwise OpenRouter).
    """
    model = model or config.lightrag_model
    raw_output = None

    for attempt in range(MAX_RETRIES):
        try:
            match model:
                case model if model.startswith("gemini"):
                    contents = f"""
        system: {system_message}
        user:{user_message}
        """
                    client = genai.Client(api_key=config.gemini_api_key)
                    response = await client.aio.models.generate_content(
                        model=model,
                        contents=[contents],
                        config=types.GenerateContentConfig(
                            response_schema=response_schema,
                            response_mime_type="application/json",
                        ),
                    )
                    raw_output = response.text
                    return jiter.from_json(raw_output.encode(encoding="utf-8"))
                case model if model.startswith("gpt"):
                    # An empty key means "not configured": let the SDK fall back to its own lookup.
                    client = AsyncOpenAI(api_key=config.openai_api_key or None)
                    response = await client.beta.chat.completions.parse(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_message},
                            {"role": "user", "content": user_message},
                        ],
                        response_format=response_schema,
                    )
                    raw_output = response.choices[0].message.content
                    return jiter.from_json(raw_output.encode(encoding="utf-8"))
                case _:
                    schema_dict = response_schema.model_json_schema()
                    schema_name = schema_dict.get("title", response_schema.__name__)

                    async with OpenRouter(api_key=config.openrouter_api_key) as client:
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
                        if config.openrouter_provider:
                            config_dict["provider"] = {
                                "name": config.openrouter_provider
                            }

                        response = await client.chat.send_async(**config_dict)
                        raw_output = response.choices[0].message.content
                        return jiter.from_json(raw_output.encode(encoding="utf-8"))
        except Exception as e:
            if isinstance(e, ValueError) and raw_output is not None:
                truncated_output = raw_output[:_RAW_OUTPUT_LOG_LIMIT]
                logger.error(
                    f"JSON parse error: {e}\n"
                    f"  Project: {config.project_label}\n"
                    f"  Model: {model}\n"
                    f"  System prompt (first 500 chars): {system_message[:500]}\n"
                    f"  User prompt (first 500 chars): {user_message[:500]}\n"
                    f"  Raw output (first {_RAW_OUTPUT_LOG_LIMIT} chars): {truncated_output}"
                )
            if not _is_retryable(e):
                logger.error(f"Non-retryable error in structured completion: {e}")
                raise
            if attempt == MAX_RETRIES - 1:
                logger.error(
                    f"Structured completion failed after {MAX_RETRIES} attempts: {e}"
                )
                raise
            delay = 2**attempt
            logger.warning(
                f"Retryable error (attempt {attempt + 1}/{MAX_RETRIES}), retrying in {delay}s: {e}"
            )
            raw_output = None
            await asyncio.sleep(delay)
