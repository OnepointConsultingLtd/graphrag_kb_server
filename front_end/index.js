import Graph from 'graphology';
import { parse } from 'graphology-gexf';
import Alpine from 'alpinejs';
import listProjects, { createHeaders } from './api.js';
import { BASE_SERVER } from './server.js';
import { createGraph, extractEdges, extractNodes } from './graph.js';
import { setToken } from './token.js';
import { setSelectedProject } from './project.js';

let token = '';

window.token = token;
window.network = null;
window.graph = null;

function loadGraph(project, token) {
    // Load the GEXF file
    fetch(
        `${BASE_SERVER}/protected/project/topics_network?project=${project}`,
        createHeaders(token),
    )
        .then(response => response.text())
        .then(gexfText => {
            const graph = parse(Graph, gexfText); // Convert GEXF to Graphology graph
            window.graph = graph;

            const { incomingDegrees, outGoingDegrees, edges } = extractEdges(
                graph.edgeEntries(),
            );

            const graphLabels = graph.nodes().reduce((a, node) => {
                return { ...a, [node]: graph.getNodeAttributes(node)['label'] };
            }, {});
            const nodes = extractNodes(
                graph.nodes(),
                graphLabels,
                incomingDegrees,
                outGoingDegrees,
            );

            createGraph(nodes, edges);

            window.project = project;
        })
        .catch(error => console.error('Error loading GEXF:', error));
}

export function changeVisibilityNodeDetails(show) {
    const nodeDetails = document.querySelector('.node-details-container');
    nodeDetails?.classList.remove(show ? 'hidden' : 'flex');
    nodeDetails?.classList.add(show ? 'flex' : 'hidden');
}

window.loadGraph = loadGraph;
window.listProjects = listProjects;

window.addEventListener('load', () => {
    window.Alpine = Alpine;
    Alpine.start();
    // Get the current URL's query parameters
    const urlParams = new URLSearchParams(window.location.search);
    const tokenValue = urlParams.get("token");
    if(tokenValue) {
        setToken(tokenValue)
        const projectValue = urlParams.get("project");
        if(projectValue) {
            setSelectedProject(projectValue)
            window.loadGraph(projectValue, tokenValue)
        }
    }
});
