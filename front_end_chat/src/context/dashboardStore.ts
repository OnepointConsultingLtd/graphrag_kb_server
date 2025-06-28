import { create } from 'zustand';
import { Project, ApiProjectsResponse, ModalType, Engine } from '../types/types';
import { ENGINES } from '../constants/engines';
import { UserData } from '../model/userData';
import { persist } from 'zustand/middleware';

export type DashboardState = {
	userData: UserData | null;
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
	widgetType: string;
	rootElementId: string;
	organisationName: string;
	searchType: string;
	additionalPromptInstructions: string;
	isSnippetSubmitting: boolean;
	snippetError: string | null;
	generatedSnippet: string | null;
	setUserData: (userData: UserData | null) => void;
	setEmail: (email: string) => void;
	setWidgetType: (widgetType: string) => void;
	setRootElementId: (rootElementId: string) => void;
	setOrganisationName: (organisationName: string) => void;
	setSearchType: (searchType: string) => void;
	setAdditionalPromptInstructions: (additionalPromptInstructions: string) => void;
	setIsSnippetSubmitting: (isSnippetSubmitting: boolean) => void;
	setSnippetError: (snippetError: string | null) => void;
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

export const useDashboardStore = create<DashboardState>()(
    persist(
        (set, get) => ({
			userData: null,
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
			widgetType: "FLOATING_CHAT",
			rootElementId: "root",
			organisationName: "My Organisation",
			searchType: "local",
			additionalPromptInstructions: "You are a helpful assistant.",
			isSnippetSubmitting: false,
			snippetError: null,
			generatedSnippet: null,
			setUserData: (userData: UserData | null) => set(() => ({ userData, email: userData?.email ?? "" })),
			setEmail: (email: string) => set({ email }),
			setWidgetType: (widgetType: string) => set({ widgetType }),
			setRootElementId: (rootElementId: string) => set({ rootElementId }),
			setOrganisationName: (organisationName: string) => set({ organisationName }),
			setSearchType: (searchType: string) => set({ searchType }),
			setAdditionalPromptInstructions: (additionalPromptInstructions: string) => set({ additionalPromptInstructions }),
			setIsSnippetSubmitting: (isSnippetSubmitting: boolean) => set({ isSnippetSubmitting }),
			setSnippetError: (snippetError: string | null) => set({ snippetError }),
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
		}),
        {
            name: "dashboard-store",
            partialize: (state) => ({
                userData: state.userData,
                projects: state.projects,
                selectedProjects: state.selectedProjects,
                isModalOpen: state.isModalOpen,
                modalType: state.modalType,
            }),
        }
    )
); 