import asyncio
import sys
from pathlib import Path

from graphrag_kb_server.service.query import rag_local_simple
from graphrag_kb_server.config import cfg
from graphrag_kb_server.logger import logger
from graphrag_kb_server.model.rag_parameters import ContextParameters


if __name__ == "__main__":
    question = "What is the value of questions?"
    project_path = None
    if len(sys.argv) > 1:
        project_path = sys.argv[1]
    if len(sys.argv) > 2:
        question = sys.argv[2]
    if project_path is None:
        logger.error("Project folder is not specified")
        sys.exit(1)
    
    project_dir = Path(project_path)
    if not project_dir.exists():
        logger.error(f"Project folder {project_path} does not exist")
        sys.exit(1)
    
    context_parameters = ContextParameters(
        query=question,
        project_dir=project_dir,
        context_size=cfg.local_context_max_tokens,
    )
    response = asyncio.run(rag_local_simple(context_parameters))
    logger.info(response)
    with open("response.html", "wt") as f:
        f.write(response)
