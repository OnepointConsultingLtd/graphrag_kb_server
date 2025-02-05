
export const BASE_SERVER = "http://localhost:9999"

export function createHeaders(token) {
    return {
        headers: {
            "accept": "*/*",
            "Authorization": `Bearer ${token}`
        }
    }
}

export default async function listProjects(token) {
    try {
        const response = await fetch(`${BASE_SERVER}/protected/projects`, createHeaders(token));
        if (!response.ok) throw new Error("Failed to fetch projects");
        const json = await response.json();
        return json["projects"].map(project => project.name);
    } catch (error) {
        console.error("Error fetching projects:", error);
        return []; // Return an empty array if there's an error
    }
}