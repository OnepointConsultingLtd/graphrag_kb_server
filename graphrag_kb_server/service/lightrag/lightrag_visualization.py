from pathlib import Path

from pyvis.network import Network
import random
import networkx as nx

from graphrag_kb_server.service.lightrag.lightrag_graph_support import (
    create_network_from_project_dir,
)


def _create_styled_network(G: nx.Graph) -> Network:
    net = Network(height="100vh", notebook=False)
    net.from_nx(G)
    # Add colors and title to nodes
    for node in net.nodes:
        node["color"] = "#{:06x}".format(random.randint(0, 0xFFFFFF))
        if "description" in node:
            node["title"] = f"{node["label"]}\n{node["description"]}"

    # Add title to edges
    for edge in net.edges:
        if "description" in edge:
            edge["title"] = edge["description"]

    return net


def get_output_path(project_dir: Path) -> Path:
    return project_dir / "lightrag" / "knowledge_graph.html"


def generate_lightrag_graph_visualization(project_dir: Path) -> Path:
    output_path = get_output_path(project_dir)
    if output_path.exists():
        return output_path

    G = create_network_from_project_dir(project_dir)

    net = _create_styled_network(G)

    # Save the network to a file in the project directory
    net.save_graph(output_path.as_posix())
    return output_path


if __name__ == "__main__":
    report = generate_lightrag_graph_visualization(
        Path("C:/var/graphrag/tennants/gil_fernandes/lightrag/dwell")
    )
    print(report.as_posix())
