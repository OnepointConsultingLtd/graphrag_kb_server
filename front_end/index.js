
import Graph from "graphology";
import { parse } from "graphology-gexf";
import { Network } from "vis-network";
import Alpine from "alpinejs";
import listProjects, { createHeaders } from "./api.js"
import { BASE_SERVER } from "./server.js";


const LIMIT = 1000

let token = ""

window.listProjects = listProjects
window.token = token


function createData(nodes, edges) {
    return { nodes, edges };
}

function createGraph(nodes, edges) {
    const data = createData(nodes, edges);

    // Define options
    const options = {
        nodes: { shape: "box" },
        physics: {
            enabled: false,
        },
    };
    const container = document.getElementById("network-container");
    const network = new Network(container, data, options)
    setTimeout(() => {
        network.moveTo({
            scale: 1.0, // Set the initial zoom factor to 0.5 (50% zoom)
            animation: true, // Disable animation for initial zoom
        });
        network.setOptions({ ...options, physics: true });
    }, 2000);
    return { options, network };
}

function extractNodes(graphNodes, graphLabels, incomingDegrees, outGoingDegrees) {
    const size = graphNodes.length
    return graphNodes.filter(node => size > LIMIT ? incomingDegrees[node] > 0 : true).map(node => {
        const incomingDegree = incomingDegrees[node] ?? 0;
        const outgoingDegree = outGoingDegrees[node] ?? 0;
        const label = `${graphLabels[node]} ${incomingDegree} ${outgoingDegree}`;
        let color = "#0084d7";
        if (incomingDegree === 0) {
            color = "gray";
        } else if (outgoingDegree === 0 && incomingDegree > 1) {
            color = "#ff6666";
        }
        return {
            "id": node, "label": label, color: color,
            font: { color: "#ffffff" }
        };
    });
}

function loadGraph(project, token) {

    // Load the GEXF file
    fetch(`${BASE_SERVER}/protected/project/topics_network?project=${project}`, createHeaders(token))
        .then(response => response.text())
        .then(gexfText => {
            const graph = parse(Graph, gexfText); // Convert GEXF to Graphology graph

            const { incomingDegrees, outGoingDegrees, edges } = extractEdges(graph.edgeEntries());

            const graphLabels = graph.nodes().reduce((a, node) => {
                return { ...a, [node]: graph.getNodeAttributes(node)['label'] }
            }, {})
            const nodes = extractNodes(graph.nodes(), graphLabels, incomingDegrees, outGoingDegrees)

            const { network } = createGraph(nodes, edges)

            network.on("doubleClick", (params) => {
                if (params.nodes.length > 0) {
                    const nodeMap = {}
                    const nodeLabels = {}
                    const edgeEntries = [...graph.edgeEntries()]
                    for (const node of graph.nodes()) {
                        nodeLabels[node] = graph.getNodeAttributes(node)['label']
                        nodeMap[node] = []
                        for (const e of graph.edges(node)) {
                            nodeMap[node] = [...nodeMap[node], edgeEntries[e]]
                        }
                    }
                    const nodes = [...params.nodes]
                    const visitedEdges = new Set()
                    const visitedNodes = new Set()
                    while (nodes.length > 0) {
                        const node = nodes.shift()
                        visitedNodes.add(node)
                        for (const edge of nodeMap[node]) {
                            visitedEdges.add(edge)
                            const fromNode = edge['source']
                            if (!visitedNodes.has(fromNode)) {
                                nodes.push(fromNode)
                            }
                            const toNode = edge['target']
                            if (!visitedNodes.has(toNode)) {
                                nodes.push(toNode)
                            }
                        }
                    }
                    const { incomingDegrees, outGoingDegrees, edges } = extractEdges([...visitedEdges])
                    const newNodes = extractNodes([...visitedNodes], nodeLabels, incomingDegrees, outGoingDegrees)
                    createGraph(newNodes, edges)
                }
            });

        })
        .catch(error => console.error("Error loading GEXF:", error));

    function extractEdges(edgeEntries) {
        const edges = [];
        const incomingDegrees = {};
        const outGoingDegrees = {};

        for (const e of edgeEntries) {
            const edgeId = e.edge;
            const { source, target } = e;
            edges.push({
                id: edgeId, from: source, to: target, label: "child of",
                arrows: {
                    to: {
                        enabled: true,
                        type: "arrow",
                    },
                }
            });
            incomingDegrees[target] = incomingDegrees[target] ? incomingDegrees[target] + 1 : 1;
            outGoingDegrees[source] = outGoingDegrees[source] ? outGoingDegrees[source] + 1 : 1;
        }
        return { incomingDegrees, outGoingDegrees, edges };
    }
}

window.loadGraph = loadGraph

window.addEventListener('load', () => {
    window.Alpine = Alpine
    Alpine.start();
})
