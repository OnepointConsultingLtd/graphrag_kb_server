
export type Engine = "graphrag" | "lightrag";

export type Project = {
	name: string;
	createdAt: string;
	fileCount: number;
	status: "active" | "archived";
	engine: Engine;
}

export type ChatTypeOptions = "full_page" | "floating" | null;

export type ApiProject = {
	id: string;
	name: string;
	updated_timestamp: string;
	input_files: unknown[];
	createdAt?: string;
}

export type ApiProjectsResponse = {
	graphrag_projects?: {
		projects: ApiProject[];
	};
	lightrag_projects?: {
		projects: ApiProject[];
	};
}

export type ModalType = 'create' | 'snippet' | 'delete' | 'update' | null;