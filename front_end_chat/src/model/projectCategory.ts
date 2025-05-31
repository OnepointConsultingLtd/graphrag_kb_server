export const Platform = {
    GRAPHRAG: "graphrag",
    LIGHTRAG: "lightrag"
} as const;

export enum SearchType {
    LOCAL = "local",
    GLOBAL = "global",
    DRIFT = "drift",
    ALL = "all",
    NAIVE = "naive"
}

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
    search_type: SearchType;
    platform: Platform;
}