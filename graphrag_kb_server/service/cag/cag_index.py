from pathlib import Path

from google import genai
from google.genai import types

from graphrag_kb_server.config import cfg, lightrag_cfg
from graphrag_kb_server.utils.cache import GenericProjectSimpleCache, GenericSimpleCache
from graphrag_kb_server.logger import logger

CAG_TTL = 60 * 60 * 2

CHAT_CACHE = GenericSimpleCache[genai.chats.Chat, str](timeout=CAG_TTL)


SYSTEM_INSTRUCTION = """
You are a highly knowledgeable and detail-oriented AI assistant. 
Your task is to carefully read and understand the document provided. 
You should accurately answer users' questions based solely on the information in the document without adding extra knowledge. 
Provide concise, clear, and contextually relevant responses while maintaining professionalism.
"""

def create_client() -> genai.Client:
    client = genai.Client(api_key=cfg.gemini_api_key)
    return client


def create_chat(client: genai.Client, cache: types.CachedContent) -> genai.chats.Chat:
    chat = client.chats.create(
        model=lightrag_cfg.lightrag_model,
        config=types.GenerateContentConfig(cached_content=cache.name),
    )
    return chat


def init_client(
    project_dir: Path, conversation_id: str, system_instruction: str = SYSTEM_INSTRUCTION
) -> genai.chats.Chat:
    cache_key = f"{project_dir.as_posix()}-{conversation_id}"
    chat = CHAT_CACHE.get(cache_key)
    if chat is not None:
        return chat
    client = create_client()
    contents = []
    for file in project_dir.glob("**/*.txt"):
        contents.append(file.read_text(encoding="utf-8"))
    cache_name = project_dir.stem
    try:
        client.caches.delete(name=cache_name)
    except Exception as e:
        logger.warning(f"Error deleting cache {cache_name}: {e}")
    cache = client.caches.create(
        model=lightrag_cfg.lightrag_model,
        config=types.CreateCachedContentConfig(
            ttl=f"{CAG_TTL}s",
            display_name=cache_name,
            system_instruction=(system_instruction),
            contents=["\n\n".join(contents)],
        ),
    )
    chat = create_chat(client, cache)
    CHAT_CACHE.set(cache_key, chat)
    return chat


def get_response(project_dir: Path, conversation_id: str, message: str) -> str:
    chat = init_client(project_dir, conversation_id)
    response = chat.send_message(message)
    return response.text


if __name__ == "__main__":
    project_dir = Path(
        "C:/var/graphrag/tennants/gil_fernandes/lightrag/learn_meditation_online/input"
    )
    response = get_response(project_dir, "1", "What can you tell me about soul consciousness and how the soul relates to God?")
    print(response)
    response = get_response(project_dir, "1", "Which was my previous question?")
    print(response)
    response = get_response(project_dir, "2", "Which was my previous question?")
    print(response)
