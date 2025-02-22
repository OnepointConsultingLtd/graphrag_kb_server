import Graph from 'graphology';
import { Network } from 'vis-network';
import { parse } from 'graphology-gexf';
import { getCommunityDetails, getCommunityEntities } from './api.js';
import getToken from './token.js';
import { changeVisibilityNodeDetails } from './index.js';

const LIMIT = 1000;
const MIN_QUERY_SIZE = 3;
const ENTITY_PREFIX = 'ENTITY_';
const COLOURS = {
    DEFAULT: '#0084d7',
    PARENT: '#ff6666',
    EDGE: 'gray',
    ENTITY: '#11aadd',
};
const DEFAULT_TEXT_COLOUR = '#ffffff';
const MAX_ENTITIES = 50

function createData(nodes, edges) {
    return { nodes, edges };
}

function handleNodeDetailsClick() {
    document
        .querySelector('.node-details-container')
        .classList.toggle('hidden');
}

export function createGraph(nodes, edges) {
    changeVisibilityNodeDetails(false);
    const data = createData(nodes, edges);

    // Define options
    const options = {
        nodes: { shape: 'box' },
        physics: {
            enabled: false,
        },
    };
    const container = document.getElementById('network-container');
    const network = new Network(container, data, options);
    setTimeout(() => {
        network.moveTo({
            scale: 1.0, // Set the initial zoom factor to 0.5 (50% zoom)
            animation: true, // Disable animation for initial zoom
        });
        network.setOptions({ ...options, physics: true });
    }, 2000);

    network.on('doubleClick', params => {
        const foundNodes = params.nodes;
        recreateGraphWithFilter(foundNodes);
    });

    network.on('oncontext', function (params) {
        params.event.preventDefault();
        const contextMenu = document.getElementById('contextMenu');
        const { x: xDOM } = params.pointer.DOM;
        contextMenu.style.top = `${params.event.clientY}px`;
        contextMenu.style.left = `${xDOM}px`;
        contextMenu.classList.remove('hidden');

        const communityId = this.getNodeAt(params.pointer.DOM);

        if (communityId?.includes(ENTITY_PREFIX)) {
            // Not a community
            return;
        }

        function addNode(newNodeId, label) {
            const nodesDataSet = network.body.data.nodes;
            const edgesDataSet = network.body.data.edges;
            const entityNodeId = `${ENTITY_PREFIX}_${newNodeId}`;

            const existingNode = !!nodesDataSet.get(entityNodeId);
            if (!existingNode) {
                nodesDataSet.add({
                    id: entityNodeId,
                    label,
                    color: COLOURS.ENTITY,
                    font: { color: DEFAULT_TEXT_COLOUR },
                });
            }
            const edgeId = `${communityId}-${entityNodeId}`;
            if (!edgesDataSet.get(edgeId)) {
                edgesDataSet.add({
                    id: edgeId,
                    from: communityId,
                    to: entityNodeId,
                });
            }
        }

        function attachEntities() {
            console.info('Getting entities for ', communityId);
            contextMenu.classList.add('hidden');
            const token = getToken();
            if (token && communityId) {
                getCommunityEntities(communityId, token).then(text => {
                    if (text) {
                        const graph = parse(Graph, text);
                        const nodes = graph.nodes();
                        for (let i = 0; i < Math.min(MAX_ENTITIES, nodes.length); i++) {
                            const node = nodes[i]
                            const label =
                                graph.getNodeAttributes(node)['label'];
                            addNode(node, label);
                        }
                    }
                });
            }
        }
        const entitiesButton = document.querySelector(
            '#contextMenu button.entities',
        );
        entitiesButton.removeEventListener('click', attachEntities);
        entitiesButton.addEventListener('click', attachEntities);
    });

    network.on('click', params => {
        contextMenu.classList.add('hidden');
        if (params.nodes.length > 0) {
            const clickedNodeId = params.nodes[0];
            const token = getToken();
            if (token) {
                const nodeDetails = document.getElementById('node-details');
                getCommunityDetails(clickedNodeId, token).then(json => {
                    const summary = json['summary'];
                    if (summary && typeof summary === 'string') {
                        changeVisibilityNodeDetails(true);
                        nodeDetails.innerHTML = `<div class="node-details-close absolute right-[6px] top-[3px]"><button class="cursor-pointer">&times;</button></div>
                            <strong>${json['title']}</strong><br /><p>${summary}</p>`;
                        const button = nodeDetails.querySelector(
                            '.node-details-close button',
                        );
                        if (button) {
                            button.removeEventListener(
                                'click',
                                handleNodeDetailsClick,
                            );
                            button.addEventListener(
                                'click',
                                handleNodeDetailsClick,
                            );
                        }
                    }
                });
            }
        }
    });

    window.network = network;

    return { options, network };
}

export function extractEdges(
    edgeEntries,
    label = 'child of',
    sourcePrefix = '',
) {
    const edges = [];
    const incomingDegrees = {};
    const outGoingDegrees = {};

    for (const e of edgeEntries) {
        const edgeId = e.edge;
        const { source, target } = e;
        edges.push({
            id: edgeId,
            from: `${sourcePrefix}${source}`,
            to: target,
            label,
            arrows: {
                to: {
                    enabled: true,
                    type: 'arrow',
                },
            },
        });
        incomingDegrees[target] = incomingDegrees[target]
            ? incomingDegrees[target] + 1
            : 1;
        outGoingDegrees[source] = outGoingDegrees[source]
            ? outGoingDegrees[source] + 1
            : 1;
    }
    return { incomingDegrees, outGoingDegrees, edges };
}

export function extractNodes(
    graphNodes,
    graphLabels,
    incomingDegrees,
    outGoingDegrees,
) {
    const size = graphNodes.length;
    return graphNodes
        .filter(node => (size > LIMIT ? incomingDegrees[node] > 0 : true))
        .map(node => {
            const incomingDegree = incomingDegrees[node] ?? 0;
            const outgoingDegree = outGoingDegrees[node] ?? 0;
            const label = `${graphLabels[node]} ${incomingDegree} ${outgoingDegree}`;
            let color = COLOURS.DEFAULT;
            if (incomingDegree === 0) {
                color = COLOURS.EDGE;
            } else if (outgoingDegree === 0 && incomingDegree > 1) {
                color = COLOURS.PARENT;
            }
            return {
                id: node,
                label: label,
                color: color,
                font: { color: DEFAULT_TEXT_COLOUR },
            };
        });
}

export function recreateGraphWithFilter(foundNodes) {
    if (foundNodes.length > 0) {
        const nodeMap = {};
        const nodeLabels = {};
        const { graph } = window;
        const edgeEntries = [...graph.edgeEntries()];
        for (const node of graph.nodes()) {
            nodeLabels[node] = graph.getNodeAttributes(node)['label'];
            nodeMap[node] = [];
            for (const e of graph.edges(node)) {
                nodeMap[node] = [...nodeMap[node], edgeEntries[e]];
            }
        }
        const nodes = [...foundNodes];
        const visitedEdges = new Set();
        const visitedNodes = new Set();
        while (nodes.length > 0) {
            const node = nodes.shift();
            visitedNodes.add(node);
            for (const edge of nodeMap[node]) {
                visitedEdges.add(edge);
                const fromNode = edge['source'];
                if (!visitedNodes.has(fromNode)) {
                    nodes.push(fromNode);
                }
                const toNode = edge['target'];
                if (!visitedNodes.has(toNode)) {
                    nodes.push(toNode);
                }
            }
        }
        const { incomingDegrees, outGoingDegrees, edges } = extractEdges([
            ...visitedEdges,
        ]);
        const newNodes = extractNodes(
            [...visitedNodes],
            nodeLabels,
            incomingDegrees,
            outGoingDegrees,
        );
        createGraph(newNodes, edges);
    }
}

export function searchGraph(event) {
    const { value } = event.target;
    if (value?.length >= MIN_QUERY_SIZE) {
        console.log('search string', value);
        const foundNodes = graph.nodes().filter(node => {
            const label = graph.getNodeAttributes(node)['label'];
            const matched = label.toLowerCase().includes(value.toLowerCase());
            if (matched) {
                console.log(label);
            }
            return matched;
        });
        if (foundNodes.length === 0) {
            alert('No results');
        }
        recreateGraphWithFilter(foundNodes);
    }
}

window.searchGraph = searchGraph;
