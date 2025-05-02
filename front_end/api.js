import { BASE_SERVER } from './server.js';

export function createHeaders(token) {
    return {
        headers: {
            accept: '*/*',
            Authorization: `Bearer ${token}`,
        },
    };
}

function throwError(response) {
    if (!response.ok)
        throw new Error(`Failed to fetch projects. Code: ${response.ok}`);
}

export default async function listProjects(token) {
    try {
        const response = await fetch(
            `${BASE_SERVER}/protected/projects`,
            createHeaders(token),
        );
        throwError(response);
        const json = await response.json();
        return json['graphrag_projects']['projects'].map(project => project.name);
    } catch (error) {
        console.error('Error fetching projects:', error);
        return []; // Return an empty array if there's an error
    }
}

export async function getCommunityDetails(id, token) {
    try {
        const response = await fetch(
            `${BASE_SERVER}/protected/project/topics_network/community/${id}?project=${window.project}`,
            createHeaders(token),
        );
        throwError(response);
        return await response.json();
    } catch (error) {
        console.error('Failed to fetch summary:', error);
        return '';
    }
}

export async function getCommunityEntities(id, token) {
    try {
        const response = await fetch(
            `${BASE_SERVER}/protected/project/topics_network/community_entities/${id}?project=${window.project}`,
            createHeaders(token),
        );
        throwError(response);
        return await response.text();
    } catch (error) {
        console.error('Failed to fetch entities:', error);
        return '';
    }
}
