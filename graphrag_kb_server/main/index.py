import sys
from pathlib import Path

from graphrag_kb_server.service.project import (
    clear_rag,
    create_graph_rag,
    create_graph_rag_cmd,
)
from graphrag_kb_server.logger import logger
from graphrag_kb_server.service.index_support import unzip_file

if __name__ == "__main__":
    type = "normal"
    indexed_folder = "/tmp/graphrag/sample"
    zip_file = Path(__file__) / "../../../docs/fitzgerald/the_great_gatsby.zip"
    if len(sys.argv) > 2:
        type = sys.argv[1]
        indexed_folder = sys.argv[2]
    else:
        sys.stderr.write("Please enter the type and the indexed folder")
        sys.exit(1)
    if len(sys.argv) > 3:
        zip_file = Path(sys.argv[2])

    assert zip_file.exists, f"The zip file ({zip_file}) does not exist."

    indexed_path = Path(indexed_folder)

    clear_rag(indexed_path)

    indexed_path.mkdir(parents=True)
    unzip_file(indexed_path, zip_file)

    if type == "cmd":
        logger.debug("Using command line calls.")
        create_graph_rag_cmd(indexed_path)
    else:
        logger.debug("Using index cli interface.")
        create_graph_rag(False, indexed_path)
