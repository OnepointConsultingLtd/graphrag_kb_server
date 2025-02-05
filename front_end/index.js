
import Graph from "graphology";
import { parse } from "graphology-gexf";
import { Network } from "vis-network";
import Alpine from "alpinejs";
import listProjects, { createHeaders, BASE_SERVER } from "./api.js"


const LIMIT = 1000

let token = ""

window.listProjects = listProjects
window.token = token

function loadGraph(project, token) {

    // Load the GEXF file
    fetch(`${BASE_SERVER}/protected/project/topics_network?project=${project}`, createHeaders(token))
        .then(response => response.text())
        .then(gexfText => {
            const graph = parse(Graph, gexfText); // Convert GEXF to Graphology graph

            const edges = []
            const incomingDegrees = {}
            const outGoingDegrees = {}

            for (const e of graph.edgeEntries()) {
                const edgeId = e.edge
                const { source, target } = e
                edges.push({
                    id: edgeId, from: source, to: target, label: "child of",
                    arrows: {
                        to: {
                            enabled: true,
                            type: "arrow",
                        },
                    }
                })
                incomingDegrees[target] = incomingDegrees[target] ? incomingDegrees[target] + 1 : 1
                outGoingDegrees[source] = outGoingDegrees[source] ? outGoingDegrees[source] + 1 : 1
            }

            const size = graph.nodes().length

            const nodes = graph.nodes().filter(node => size > LIMIT ? incomingDegrees[node] > 0 : true).map(node => {
                const incomingDegree = incomingDegrees[node] ?? 0
                const outgoingDegree = outGoingDegrees[node] ?? 0
                const label = `${graph.getNodeAttributes(node)['label']} ${incomingDegree} ${outgoingDegree}`
                let color = "#0084d7"
                if (incomingDegree === 0) {
                    color = "gray"
                } else if (outgoingDegree === 0 && incomingDegree > 1) {
                    color = "#ff6666"
                }
                return {
                    "id": node, "label": label, color: color,
                    font: { color: "#ffffff" }
                }
            })

            const data = {
                nodes: nodes,
                edges: edges,
            };
            // Get the container for Sigma.js
            const container = document.getElementById("network-container");
            // Define options
            const options = {
                nodes: { shape: "box" },
                physics: {
                    enabled: false,
                },
            };
            const network = new Network(container, data, options);

            setTimeout(() => {
                network.moveTo({
                    scale: 1.0, // Set the initial zoom factor to 0.5 (50% zoom)
                    animation: true, // Disable animation for initial zoom
                });
                network.setOptions({ ...options, physics: true });
            }, 2000);

            // Initialize and render Sigma.js
            // new Sigma(graph, container);


        })
        .catch(error => console.error("Error loading GEXF:", error));
}

window.loadGraph = loadGraph

window.addEventListener('load', () => {
    window.Alpine = Alpine
    Alpine.start();
})
