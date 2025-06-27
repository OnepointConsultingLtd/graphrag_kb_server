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

export const ENGINE_NAME_SEPARATOR = ':::';

function getProjectOptions(json, projectEngine) {
    return json[`${projectEngine}_projects`]['projects']
        .map(project => ({ label: `[${projectEngine}] ${project.name}`, value: `${projectEngine}${ENGINE_NAME_SEPARATOR}${project.name}` }));
}

export default async function listProjects(token) {
    try {
        const response = await fetch(
            `${BASE_SERVER}/protected/projects`,
            createHeaders(token),
        );
        throwError(response);
        const json = await response.json();
        const projects = getProjectOptions(json, 'graphrag');
        const lightrag_projects = getProjectOptions(json, 'lightrag');
        return [...projects, ...lightrag_projects];
    } catch (error) {
        console.error('Error fetching projects:', error);
        return []; // Return an empty array if there's an error
    }
}

export async function getCommunityDetails(id, token) {
    const [engine, projectName] = window.project.split(ENGINE_NAME_SEPARATOR);
    try {
        const response = await fetch(
            `${BASE_SERVER}/protected/project/topics_network/community/${id}?project=${projectName}&engine=${engine}`,
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
    const project = window.project.replace(/.+?\:+/, "")
    try {
        const response = await fetch(
            `${BASE_SERVER}/protected/project/topics_network/community_entities/${id}?project=${project}`,
            createHeaders(token),
        );
        throwError(response);
        return await response.text();
    } catch (error) {
        console.error('Failed to fetch entities:', error);
        return '';
    }
}
