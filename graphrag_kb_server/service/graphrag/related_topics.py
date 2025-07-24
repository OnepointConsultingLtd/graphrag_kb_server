from pathlib import Path
import networkx as nx

from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.model.topics import SimilarityTopics, SimilarityTopicsRequest
from graphrag_kb_server.service.graphrag.graph_support import read_graphrag_project
from graphrag_kb_server.service.similar_topics import (
    get_sorted_related_entities_simple_rerank,
)
from graphrag_kb_server.utils.cache import GenericSimpleCache
from graphrag_kb_server.service.graphrag.query import prepare_local_search
from graphrag_kb_server.model.rag_parameters import ContextParameters

from graphrag.query.context_builder.entity_extraction import (
    map_query_to_entities,
)


graph_cache = GenericSimpleCache[nx.classes.graph.Graph, Path]()


def get_related_topics_graphrag(
    request: SimilarityTopicsRequest,
) -> SimilarityTopics | None:
    project_dir = request.project_dir
    G = graph_cache.get(project_dir)
    if G is None:
        G = read_graphrag_project(request.project_dir)
        graph_cache.set(project_dir, G)

    if not request.source:
        search_engine = prepare_local_search(
            ContextParameters(
                query=request.text, project_dir=request.project_dir, context_size=5000
            )
        )
        context_builder = search_engine.context_builder
        entities = map_query_to_entities(
            query=request.text,
            text_embedding_vectorstore=context_builder.entity_text_embeddings,
            text_embedder=context_builder.text_embedder,
            all_entities_dict=context_builder.entities,
            embedding_vectorstore_key=context_builder.embedding_vectorstore_key,
            include_entity_names=[],
            exclude_entity_names=[],
            k=8,
            oversample_scaler=2,
        )
        titles = [entity.title for entity in entities if entity.title in G.nodes()]
        if len(titles) > 0:
            params = request.model_dump()
            params["source"] = titles[0]
            request = SimilarityTopicsRequest(**params)
        else:
            return None

    if request.source not in G.nodes():
        return None
    return get_sorted_related_entities_simple_rerank(G, request)


if __name__ == "__main__":
    from pathlib import Path

    project_dir = Path("/var/graphrag/tennants/gil_fernandes/graphrag/lmo")
    assert project_dir.exists()
    similarity_topics = get_related_topics_graphrag(
        SimilarityTopicsRequest(
            project_dir=project_dir, source="MEDITATION", engine=Engine.GRAPHRAG
        )
    )
    if similarity_topics is not None:
        for st in similarity_topics.topics:
            print(st.name, st.probability)
