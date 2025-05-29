import { BASE_SERVER } from "./server";

function createHeaders(jwt: string) {
    return {
        headers: {
            Authorization: `Bearer ${jwt}`,
        },
    }
}

export async function fetchProjects(jwt: string) {
    try {
        const response = await fetch(`${BASE_SERVER}/protected/projects`, createHeaders(jwt));
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

