import { Network } from "vis-network";
import { getCommunityDetails } from "./api.js"
import Alpine from "alpinejs";
import {changeVisibilityNodeDetails } from "./index.js"

const LIMIT = 1000
const MIN_QUERY_SIZE = 3

function createData(nodes, edges) {
    return { nodes, edges };
}

export function createGraph(nodes, edges) {
    changeVisibilityNodeDetails(false)
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

    network.on("doubleClick", (params) => {
        const foundNodes = params.nodes
        recreateGraphWithFilter(foundNodes)
    });

    network.on("click", (params) => {
        if (params.nodes.length > 0) {
            const clickedNodeId = params.nodes[0];
            const token = Alpine.$data(document.querySelector('[x-ref="main"]')).token
            if (token) {
                getCommunityDetails(clickedNodeId, token)
                    .then(json => {
                        const summary = json["summary"]
                        if (summary && typeof summary === "string") {
                            changeVisibilityNodeDetails(true)
                            document.getElementById("node-details").innerHTML = `<strong>${json["title"]}</strong><br /><p>${summary}</p>`
                        }
                    })
            }
        }
    })

    window.network = network

    return { options, network };
}

export function extractEdges(edgeEntries) {
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

export function extractNodes(graphNodes, graphLabels, incomingDegrees, outGoingDegrees) {
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

export function recreateGraphWithFilter(foundNodes) {
    if (foundNodes.length > 0) {
        const nodeMap = {}
        const nodeLabels = {}
        const { graph } = window
        const edgeEntries = [...graph.edgeEntries()]
        for (const node of graph.nodes()) {
            nodeLabels[node] = graph.getNodeAttributes(node)['label']
            nodeMap[node] = []
            for (const e of graph.edges(node)) {
                nodeMap[node] = [...nodeMap[node], edgeEntries[e]]
            }
        }
        const nodes = [...foundNodes]
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
}

export function searchGraph(event) {
    const { value } = event.target
    if (value?.length >= MIN_QUERY_SIZE) {
        console.log('search string', value)
        const foundNodes = graph.nodes().filter(node => {
            const label = graph.getNodeAttributes(node)['label']
            const matched = label.toLowerCase().includes(value.toLowerCase());
            if (matched) { console.log(label) };
            return matched
        })
        if (foundNodes.length === 0) {
            alert("No results")
        }
        recreateGraphWithFilter(foundNodes)
    }
}

window.searchGraph = searchGraph

