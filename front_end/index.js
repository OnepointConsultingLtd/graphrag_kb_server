
import Graph from "graphology";
import { parse } from "graphology-gexf";
import Alpine from "alpinejs";
import listProjects, { createHeaders } from "./api.js"
import { BASE_SERVER } from "./server.js";
import { createGraph, recreateGraphWithFilter, extractEdges, extractNodes } from "./graph.js";

let token = ""

window.token = token
window.network = null
window.graph = null

function loadGraph(project, token) {

    // Load the GEXF file
    fetch(`${BASE_SERVER}/protected/project/topics_network?project=${project}`, createHeaders(token))
        .then(response => response.text())
        .then(gexfText => {
            const graph = parse(Graph, gexfText); // Convert GEXF to Graphology graph
            window.graph = graph

            const { incomingDegrees, outGoingDegrees, edges } = extractEdges(graph.edgeEntries());

            const graphLabels = graph.nodes().reduce((a, node) => {
                return { ...a, [node]: graph.getNodeAttributes(node)['label'] }
            }, {})
            const nodes = extractNodes(graph.nodes(), graphLabels, incomingDegrees, outGoingDegrees)

            createGraph(nodes, edges)

        })
        .catch(error => console.error("Error loading GEXF:", error));
}

window.loadGraph = loadGraph
window.listProjects = listProjects

window.addEventListener('load', () => {
    window.Alpine = Alpine
    Alpine.start();
})
