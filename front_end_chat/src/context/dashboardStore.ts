import { create } from 'zustand';
import { DashboardState, Project, ApiProjectsResponse } from '../types/types';
import { ENGINES } from '../constants/engines';

export const useDashboardStore = create<DashboardState>((set, get) => ({
	projects: [],
	selectedProjects: [],
	isModalOpen: false,
	modalType: null,

	// Create Project Modal States
	projectName: "",
	engine: ENGINES.GRAPHRAG,
	incremental: false,
	file: null,
	isSubmitting: false,
	error: null,

	// Generate Snippet Modal States
	email: "john.doe@gmail.com",
	setEmail: (email: string) => set({ email }),
	widgetType: "FLOATING_CHAT",
	setWidgetType: (widgetType: string) => set({ widgetType }),
	rootElementId: "root",
	setRootElementId: (rootElementId: string) => set({ rootElementId }),
	organisationName: "My Organisation",
	setOrganisationName: (organisationName: string) => set({ organisationName }),
	searchType: "local",
	setSearchType: (searchType: string) => set({ searchType }),
	additionalPromptInstructions: "You are a helpful assistant.",
	setAdditionalPromptInstructions: (additionalPromptInstructions: string) => set({ additionalPromptInstructions }),
	isSnippetSubmitting: false,
	setIsSnippetSubmitting: (isSnippetSubmitting: boolean) => set({ isSnippetSubmitting }),
	snippetError: null,
	setSnippetError: (snippetError: string | null) => set({ snippetError }),
	generatedSnippet: null,
	setGeneratedSnippet: (generatedSnippet: string | null) => set({ generatedSnippet }),

	// Create Project Modal Actions
	setProjectName: (name) => set({ projectName: name }),
	setEngine: (engine) => set({ engine }),
	setIncremental: (incremental) => set({ incremental }),
	setFile: (file) => set({ file }),
	setIsSubmitting: (isSubmitting) => set({ isSubmitting }),
	setError: (error) => set({ error }),


	addProject: (projectName, engine) => {
		const newProject: Project = {
			name: projectName,
			createdAt: new Date().toISOString().split('T')[0],
			fileCount: 1,
			status: 'active',
			engine: engine,
		};
		set((state) => {
			if (Array.isArray(state.projects)) {
				return { projects: [newProject, ...state.projects] };
			}
			// If projects is not an array, convert it to array format
			return { projects: [newProject] };
		});
	},

	toggleProjectSelection: (id) => {
		set((state) => ({
			selectedProjects: state.selectedProjects.includes(id)
				? state.selectedProjects.filter((pId) => pId !== id)
				: [...state.selectedProjects, id],
		}));
	},


	openModal: (type) => set({ modalType: type, isModalOpen: true }),
	closeModal: () => set({ modalType: null, isModalOpen: false }),


	// Reset Create Project Form
	resetCreateProjectForm: () => set({
		projectName: "",
		engine: ENGINES.GRAPHRAG,
		incremental: false,
		file: null,
		error: null
	}),

	getSelectedProjects: () => {
		const { projects, selectedProjects } = get();
		if (Array.isArray(projects)) {
			return projects.filter(p => selectedProjects.includes(p.name));
		}
		// If projects is not an array, return empty array for now
		return [];
	},

	setProjects: (projects: Project[] | ApiProjectsResponse) => set({ projects })
})); 