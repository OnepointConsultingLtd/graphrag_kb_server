from graphrag_kb_server.service.google_ai_client import structured_completion
from graphrag_kb_server.model.topics import Topics, TopicQuestions
from graphrag_kb_server.prompt_loader import prompts


async def generate_questions(topics: Topics) -> TopicQuestions:
    topics_str = "\n\n".join([topic.markdown() for topic in topics.topics])
    user_prompt = prompts["question-generation"]["user_prompt"].format(topics=topics_str)
    topic_questions_dict = await structured_completion(
        prompts["question-generation"]["system_prompt"], user_prompt, TopicQuestions
    )
    return TopicQuestions(**topic_questions_dict)
    
