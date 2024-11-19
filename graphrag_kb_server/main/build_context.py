import sys

from graphrag_kb_server.service.query import rag_local_build_context
from graphrag_kb_server.logger import logger
from graphrag_kb_server.config import cfg

if __name__ == "__main__":
    question = "What is the value of questions?"
    if len(sys.argv) > 1:
        question = sys.argv[1]
    context_text, context_records = rag_local_build_context(
        question, cfg.graphrag_root_dir_path
    )
    logger.info(f"==== Text =====")
    logger.info(context_text)
