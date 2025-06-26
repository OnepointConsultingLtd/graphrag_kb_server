
export type Engine = "graphrag" | "lightrag";

export type Project = {
	name: string;
	createdAt: string;
	fileCount: number;
	status: "active" | "archived";
	engine: Engine;
}

export type ChatTypeOptions = "full_page" | "floating";

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

export type DashboardState = {
	projects: Project[] | ApiProjectsResponse;
	selectedProjects: string[];
	isModalOpen: boolean;
	modalType: ModalType;

	// Create Project Modal States
	projectName: string;
	engine: Engine;
	incremental: boolean;
	file: File | null;
	isSubmitting: boolean;
	error: string | null;

	// Generate Snippet Modal States
	email: string;
	setEmail: (email: string) => void;
	widgetType: string;
	setWidgetType: (widgetType: string) => void;
	rootElementId: string;
	setRootElementId: (rootElementId: string) => void;
	organisationName: string;
	setOrganisationName: (organisationName: string) => void;
	searchType: string;
	setSearchType: (searchType: string) => void;
	additionalPromptInstructions: string;
	setAdditionalPromptInstructions: (additionalPromptInstructions: string) => void;
	isSnippetSubmitting: boolean;
	setIsSnippetSubmitting: (isSnippetSubmitting: boolean) => void;
	snippetError: string | null;
	setSnippetError: (snippetError: string | null) => void;
	generatedSnippet: string | null;
	setGeneratedSnippet: (generatedSnippet: string | null) => void;

	// Actions
	addProject: (projectName: string, engine: Engine) => void;
	toggleProjectSelection: (id: string) => void;
	setProjects: (projects: Project[] | ApiProjectsResponse) => void;

	// Modal controls
	openModal: (type: ModalType) => void;
	closeModal: () => void;

	// Create Project Modal Actions
	setProjectName: (name: string) => void;
	setEngine: (engine: Engine) => void;
	setIncremental: (incremental: boolean) => void;
	setFile: (file: File | null) => void;
	setIsSubmitting: (isSubmitting: boolean) => void;
	setError: (error: string | null) => void;
	resetCreateProjectForm: () => void;

	// Selectors
	getSelectedProjects: () => Project[];
}