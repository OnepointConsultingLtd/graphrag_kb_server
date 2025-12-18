

import datetime
from datetime import datetime
from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.model.project import FullProject, IndexingStatus, Project
from graphrag_kb_server.test.service.db.common_test_support import DEFAULT_SCHEMA_NAME


def create_test_project():
    return FullProject(
        schema_name=DEFAULT_SCHEMA_NAME,
        engine=Engine.GRAPHRAG,
        project=Project(
            name="test_project",
            updated_timestamp=datetime.now(),
            input_files=[],
            indexing_status=IndexingStatus.NOT_STARTED,
        ),
    )