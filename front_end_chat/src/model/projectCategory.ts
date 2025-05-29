export const Platform = {
    GRAPHRAG: "GraphRAG",
    LIGHTRAG: "LightRAG"
} as const;

export type Platform = typeof Platform[keyof typeof Platform];

export type Projects = {
    projects: Project[];
}

export type ProjectCategories = {
    graphrag_projects: Projects;
    lightrag_projects: Projects;
}

export type Project = {
    name: string;
    updated_timestamp: Date;
    input_files: string[];
}