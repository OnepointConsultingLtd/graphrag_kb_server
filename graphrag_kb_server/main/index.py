import sys
from graphrag_kb_server.service.project import (
    clear_rag,
    create_graph_rag,
    create_graph_rag_cmd,
)
from graphrag_kb_server.logger import logger

if __name__ == "__main__":
    type = "normal"
    if len(sys.argv) > 1:
        type = sys.argv[1]
    clear_rag()
    if type == "cmd":
        logger.debug("Using command line calls.")
        create_graph_rag_cmd()
    else:
        logger.debug("Using index cli interface.")
        create_graph_rag()
