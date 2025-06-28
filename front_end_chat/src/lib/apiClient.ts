import type { Project } from "../model/projectCategory";
import type { Reference } from "../model/references";
import { getBaseServer } from "./server";
import type { Query } from "../model/query";
import type { ChatMessage } from "../model/message";
import { ChatMessageType } from "../model/message";

function createHeaders(jwt: string) {
    return {
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${jwt}`,
        },
    }
}

export async function validateToken(token: string) {
    const response = await fetch(
        `${getBaseServer()}/token/validate_token?token=${token}`,
        {
            method: "POST",
            headers: {
                ...createHeaders(token).headers
            }
        }
    );
    if (!response.ok) {
        throw new Error(`Token validation failed. Error code: ${response.status}. Error: ${response.statusText}`);
    }
    return await response.json();
}

export async function fetchProjects(jwt: string) {
    try {
        const response = await fetch(`${getBaseServer()}/protected/projects`, createHeaders(jwt));
        if (!response.ok) {
            throw new Error(`Failed to fetch projects. Error code: ${response.status}. Error: ${response.statusText}`);
        }
        return await response.json();
    } catch (error: unknown) {
        // This block handles network-level errors (e.g., CORS, DNS, bad headers)
        if (error instanceof TypeError) {
            // Typical for network issues or CORS problems
            throw new Error(`Network error while fetching projects: ${error.message}`);
        } else if (error instanceof Error) {
            // Re-throw known errors with more context
            throw new Error(`Unexpected error: ${error.message}`);
        } else {
            // Unknown failure mode
            throw new Error(`Unknown error during fetchProjects`);
        }
    }
}

export function convertChatHistoryToLightragChatHistory(chatHistory: ChatMessage[]) {
    const maxSize = 10;
    return chatHistory.map((message) => ({
        role: message.type === ChatMessageType.USER ? "user" : "assistant",
        content: message.text
    })).slice(0, maxSize);
}


export async function sendQuery(query: Query) {
    const { jwt, question, project, chatHistory } = query;
    const params = new URLSearchParams();
    params.set("project", project.name);
    params.set("engine", project.platform);
    const response = await fetch(`${getBaseServer()}/protected/project/chat?${params.toString()}`, {
        ...createHeaders(jwt),
        method: 'POST',
        headers: {
            ...createHeaders(jwt).headers
        },
        body: JSON.stringify({
            "question": question,
            "search": project.search_type,
            "format": "json",
            "context_size": 14000,
            "system_prompt_additional": project.additional_prompt_instructions,
            "include_context": true,
            "structured_output": true,
            "chat_history": convertChatHistoryToLightragChatHistory(chatHistory)
        })
    });
    if (!response.ok) {
        throw new Error(`Failed to fetch projects. Error code: ${response.status}. Error: ${response.statusText}`);
    }
    return await response.json();
}

export async function downloadFile(jwt: string, project: Project, reference: Reference, originalFile: boolean = false): Promise<Response> {
    const params = new URLSearchParams();
    params.set("project", project.name);
    params.set("engine", project.platform);
    params.set("file", reference.path || "");
    params.set("summary", "false");
    if (originalFile) {
        params.set("original_file", "true");
    }
    const response = await fetch(`${getBaseServer()}/protected/project/download/single_file?${params.toString()}`, createHeaders(jwt));
    if (!response.ok) {
        throw new Error(`Failed to download file. Error code: ${response.status}. Error: ${response.statusText}`);
    }
    return response;
}
