export type Engine = "graphrag" | "lightrag";

export type Project = {
	id: string;
	name: string;
	createdAt: string;
	fileCount: number;
	status: "active" | "archived";
	engine: Engine;

}

export type ModalType = 'create' | 'snippet' | 'delete' | 'update' | null;

export type DashboardState = {
	projects: Project[];
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