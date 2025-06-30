from graphrag_kb_server.model.rag_parameters import QueryParameters
from graphrag_kb_server.model.rag_parameters import ContextParameters


def inject_system_prompt_to_query_params(
    query_params: QueryParameters,
) -> ContextParameters:
    """
    Inject the system prompt to the query parameters.
    """
    context_params = query_params.context_params
    system_prompt = query_params.system_prompt_additional
    if system_prompt and len(system_prompt) > 0:
        query = f"""Question: {context_params.query}
Additional Instructions: {system_prompt}
"""
        return ContextParameters(
            query=query,
            project_dir=context_params.project_dir,
            context_size=context_params.context_size,
        )
    return context_params
