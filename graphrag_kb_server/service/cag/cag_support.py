from pathlib import Path
from typing import Generator

from google import genai
from google.genai import types


from graphrag_kb_server.config import cfg, lightrag_cfg
from graphrag_kb_server.utils.cache import GenericSimpleCache, PersistentSimpleCache
from graphrag_kb_server.logger import logger
from graphrag_kb_server.model.topics import Topics

CAG_TTL = 60 * 60 * 2  # 2 hours

CHAT_CACHE = GenericSimpleCache[genai.chats.Chat, str](timeout=CAG_TTL)

TOPICS_CACHE = PersistentSimpleCache[Topics](key="topics")

INITIAL_CONVERSATION_ID = "1"

SYSTEM_INSTRUCTION = """
You are a highly knowledgeable and detail-oriented AI assistant. 
Your task is to carefully read and understand the document provided. 
You should accurately answer users' questions based solely on the information in the document without adding extra knowledge. 
Provide concise, clear, and contextually relevant responses while maintaining professionalism.
"""


def _create_client() -> genai.Client:
    client = genai.Client(api_key=cfg.gemini_api_key)
    return client


async def _create_chat(
    client: genai.Client, cache: types.CachedContent
) -> genai.chats.Chat:
    chat = client.aio.chats.create(
        model=lightrag_cfg.lightrag_model,
        config=types.GenerateContentConfig(cached_content=cache.name),
    )
    return chat


def _create_content(project_dir: Path) -> list[str]:
    contents = []
    for file in project_dir.glob("**/*.txt"):
        logger.info(f"Adding file {file.as_posix()}")
        contents.append(file.read_text(encoding="utf-8"))
    return contents


async def acreate_cag(
    project_dir: Path,
    conversation_id: str,
    system_instruction: str = SYSTEM_INSTRUCTION,
) -> genai.chats.Chat:
    cache_key = f"{project_dir.as_posix()}-{conversation_id}"
    chat = CHAT_CACHE.get(cache_key)
    if chat is not None:
        return chat
    client = _create_client()
    contents = _create_content(project_dir)
    cache_name = project_dir.stem
    try:
        cache = await client.aio.caches.get(name=cache_name)
        if cache is not None:
            await client.aio.caches.delete(name=cache_name)
    except Exception as e:
        logger.warning(f"Error deleting cache {cache_name}: {e}")
    cache = await client.aio.caches.create(
        model=lightrag_cfg.lightrag_model,
        config=types.CreateCachedContentConfig(
            ttl=f"{CAG_TTL}s",
            display_name=cache_name,
            system_instruction=(system_instruction),
            contents=[contents],
        ),
    )
    logger.info(f"Created cache {cache.display_name}")
    logger.info(f"Cache contents: {cache.usage_metadata.total_token_count}")
    chat = await _create_chat(client, cache)
    CHAT_CACHE.set(cache_key, chat)
    if conversation_id == INITIAL_CONVERSATION_ID:
        await extract_main_topics(project_dir)
    return chat


async def extract_main_topics(project_dir: Path) -> Topics:
    if TOPICS_CACHE.get(project_dir) is not None:
        return TOPICS_CACHE.get(project_dir)
    client = _create_client()
    system_instruction = """
    You are a highly knowledgeable and detail-oriented AI assistant. 
    Your task is to carefully read and understand the document provided and to extract the main topics of the document.
    The topics should be in the following format:
    - name: The name of the topic
    - description: The description of the topic
    - type: The type of the topic
    - questions: The questions associated with the topic
    
    """
    contents = _create_content(project_dir)
    response = await client.aio.models.generate_content(
        model=lightrag_cfg.lightrag_model,
        contents=[contents],
        config=types.GenerateContentConfig(
            response_schema=Topics,
            response_mime_type="application/json",
            system_instruction=system_instruction,
        ),
    )
    topics = Topics.model_validate_json(response.text)
    TOPICS_CACHE.set(project_dir, topics)
    return topics


async def cag_get_response(
    project_dir: Path, conversation_id: str, message: str
) -> str:
    chat = await acreate_cag(project_dir, conversation_id)
    response = await chat.send_message(message)
    return response.text


async def cag_get_response_stream(
    project_dir: Path, conversation_id: str, message: str
) -> Generator[types.GenerateContentResponse, None, None]:
    chat = await acreate_cag(project_dir, conversation_id)
    return await chat.send_message_stream(message)


if __name__ == "__main__":
    import asyncio

    project_dir = Path("C:/var/graphrag/tennants/gil_fernandes/lightrag/gothic/input")

    async def main(project_dir: Path, question1: str, question2: str, question3: str):
        response = await cag_get_response(
            project_dir,
            "1",
            question1,
        )
        print(response)
        response = await cag_get_response(project_dir, "1", question2)
        print(response)
        response = await cag_get_response(project_dir, "2", question2)
        print(response)
        stream = await cag_get_response_stream(project_dir, "2", question3)
        async for event in stream:
            print(event.text, sep="", end="", flush=True)
        print("# topics")
        topics = await extract_main_topics(project_dir)
        for topic in topics.topics:
            print(topic.name)
            print(topic.description)
            print(topic.type)
            print(topic.questions)
        print()

    # asyncio.run(
    #     main(
    #         Path(
    #             "C:/var/graphrag/tennants/gil_fernandes/lightrag/learn_meditation_online/input"
    #         ),
    #         "What can you tell me about soul consciousness and how the soul relates to God?",
    #         "Which was my previous question?",
    #         "How important is relaxation?",
    #     )
    # )

    asyncio.run(
        main(
            Path("C:/var/graphrag/tennants/gil_fernandes/lightrag/gothic/input"),
            "What can you tell me about the phantom of the opera?",
            "Which was my previous question?",
            "Can you summarize the plot of Carmilla?",
        )
    )
