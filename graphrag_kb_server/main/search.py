import asyncio
import sys
from graphrag_kb_server.service.query import rag_local
from graphrag_kb_server.config import cfg
from graphrag_kb_server.logger import logger


if __name__ == "__main__":
    question = "What is the value of questions?"
    if len(sys.argv) > 1:
        question = sys.argv[1]
    response = asyncio.run(rag_local(question, cfg.graphrag_root_dir_path))
    logger.info(response)
    with open("response.html", "wt") as f:
        f.write(response)
