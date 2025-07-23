import { create } from "zustand";
import {
  Project,
  ApiProjectsResponse,
  ModalType,
  Engine,
} from "../model/types";
import { ENGINES } from "../constants/engines";
import { UserData } from "../model/userData";
import { persist } from "zustand/middleware";
import { GENERATE_SNIPPET_MODAL_ID } from "../components/dashboard/GenerateSnippetModal";
import { showCloseModal } from "../lib/dialog";
import { GENERATE_URL_MODAL_ID } from "../components/dashboard/GenerateURLModal";

function openSnippetModalDialogue(open: boolean) {
  showCloseModal(open, GENERATE_SNIPPET_MODAL_ID);
}

function toggleGenerateUrlDialog(isOpen: boolean) {
  showCloseModal(isOpen, GENERATE_URL_MODAL_ID);
}

export type DashboardState = {
  userData: UserData | null;
  projects: Project[] | ApiProjectsResponse;
  selectedProjects: string[];
  isModalOpen: boolean;
  modalType: ModalType | null;

  // Create Project Modal States
  projectName: string;
  engine: Engine;
  incremental: boolean;
  file: File | null;
  isSubmitting: boolean;
  uploadSuccessMessage: string | null;

  // Message States
  success: string | null;
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
  generateUrlDialogOpen: boolean;
  snippetModalDialogueOpen: boolean;
  isGenerateUrlSubmitting: boolean;
  generateUrl: string | null;
  generateUrlError: string | null;
  expandedSections: Record<string, boolean>;
  setUserData: (userData: UserData | null) => void;
  setEmail: (email: string) => void;
  setWidgetType: (widgetType: string) => void;
  setRootElementId: (rootElementId: string) => void;
  setOrganisationName: (organisationName: string) => void;
  setSearchType: (searchType: string) => void;
  setAdditionalPromptInstructions: (
    additionalPromptInstructions: string,
  ) => void;
  setIsSnippetSubmitting: (isSnippetSubmitting: boolean) => void;
  setSnippetError: (snippetError: string | null) => void;
  setGeneratedSnippet: (generatedSnippet: string | null) => void;
  setExpandedSection: (platform: string, isExpanded: boolean) => void;

  // Actions
  addProject: (projectName: string, engine: Engine) => void;
  toggleProjectSelection: (id: string) => void;
  setProjects: (projects: Project[] | ApiProjectsResponse) => void;

  // Modal controls
  openModal: (type: ModalType) => void;
  openModalWithProject: (type: ModalType, projectName: string) => void;
  closeModal: () => void;

  // Create Project Modal Actions
  setProjectName: (name: string) => void;
  setEngine: (engine: Engine) => void;
  setIncremental: (incremental: boolean) => void;
  setFile: (file: File | null) => void;
  setIsSubmitting: (isSubmitting: boolean) => void;
  setUploadSuccessMessage: (uploadSuccessMessage: string | null) => void;
  resetCreateProjectForm: () => void;

  // Selectors
  getSelectedProjects: () => Project[];
  logout: () => void;

  // Message States
  setSuccess: (success: string | null) => void;
  setError: (error: string | null) => void;

  // Generate URL Modal States
  setSnippetModalDialogueOpen: (snippetModalDialogueOpen: boolean) => void;
  setGenerateUrlDialogOpen: (generateUrlDialogOpen: boolean) => void;
  setIsGenerateUrlSubmitting: (isGenerateUrlSubmitting: boolean) => void;
  setGenerateUrl: (generateUrl: string | null) => void;
  setGenerateUrlError: (generateUrlError: string | null) => void;
};

export const useDashboardStore = create<DashboardState>()(
  persist(
    (set, get) => {
      return {
        userData: null,
        projects: [],
        selectedProjects: [],
        isModalOpen: false,
        modalType: null,

        // Create Project Modal States
        projectName: "",
        engine: ENGINES.LIGHTRAG,
        incremental: false,
        file: null,
        isSubmitting: false,
        uploadSuccessMessage: null,

        // Message States
        success: null,
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
        generateUrlDialogOpen: false,
        snippetModalDialogueOpen: false,
        isGenerateUrlSubmitting: false,
        generateUrl: null,
        generateUrlError: null,
        expandedSections: {},
        setUserData: (userData: UserData | null) =>
          set(() => ({ userData, email: userData?.email ?? "" })),
        setEmail: (email: string) => set({ email }),
        setWidgetType: (widgetType: string) => set({ widgetType }),
        setRootElementId: (rootElementId: string) => set({ rootElementId }),
        setOrganisationName: (organisationName: string) =>
          set({ organisationName }),
        setSearchType: (searchType: string) => set({ searchType }),
        setAdditionalPromptInstructions: (
          additionalPromptInstructions: string,
        ) => set({ additionalPromptInstructions }),
        setIsSnippetSubmitting: (isSnippetSubmitting: boolean) =>
          set({ isSnippetSubmitting }),
        setSnippetError: (snippetError: string | null) => set({ snippetError }),
        setGeneratedSnippet: (generatedSnippet: string | null) =>
          set({ generatedSnippet }),
        setExpandedSection: (platform: string, isExpanded: boolean) =>
          set({
            expandedSections: {
              ...get().expandedSections,
              [platform]: isExpanded,
            },
          }),

        // Create Project Modal Actions
        setProjectName: (name) => set({ projectName: name }),
        setEngine: (engine) => set({ engine }),
        setIncremental: (incremental) => set({ incremental }),
        setFile: (file) => set({ file }),
        setIsSubmitting: (isSubmitting) => set({ isSubmitting }),

        // Message States
        setSuccess: (success) => set({ success }),
        setError: (error) => set({ error }),

        setUploadSuccessMessage: (uploadSuccessMessage) =>
          set({ uploadSuccessMessage }),

        addProject: (projectName, engine) => {
          const newProject: Project = {
            name: projectName,
            createdAt: new Date().toISOString().split("T")[0],
            fileCount: 1,
            status: "active",
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
        openModal: (type) =>
          set(() => {
            return {
              modalType: type,
              isModalOpen: true,
              incremental: type === ModalType.UPDATE,
              success: null,
              error: null,
            };
          }),
        openModalWithProject: (type, projectName) =>
          set({
            modalType: type,
            isModalOpen: true,
            incremental: type === ModalType.UPDATE,
            projectName: projectName,
            success: null,
            error: null,
          }),
        closeModal: () =>
          set(() => {
            return {
              modalType: null,
              isModalOpen: false,
              projectName: "",
              success: null,
              error: null,
            };
          }),

        // Reset Create Project Form
        resetCreateProjectForm: () =>
          set({
            projectName: "",
            engine: ENGINES.GRAPHRAG,
            incremental: false,
            file: null,
            error: null,
            uploadSuccessMessage: null,
          }),

        getSelectedProjects: () => {
          const { projects, selectedProjects } = get();
          if (Array.isArray(projects)) {
            return projects.filter((p) => selectedProjects.includes(p.name));
          }
          // If projects is not an array, return empty array for now
          return [];
        },

        setProjects: (projects: Project[] | ApiProjectsResponse) =>
          set({ projects }),

        logout: () =>
          set({
            userData: null,
            email: "john.doe@gmail.com",
            projects: [],
            selectedProjects: [],
            isModalOpen: false,
            modalType: null,
            projectName: "",
            engine: ENGINES.LIGHTRAG,
            incremental: false,
            file: null,
            isSubmitting: false,
            uploadSuccessMessage: null,
            success: null,
            error: null,
            expandedSections: {},
          }),
        setSnippetModalDialogueOpen: (snippetModalDialogueOpen: boolean) =>
          set(() => {
            openSnippetModalDialogue(snippetModalDialogueOpen);
            return { snippetModalDialogueOpen };
          }),
        setGenerateUrlDialogOpen: (generateUrlDialogOpen: boolean) =>
          set(() => {
            toggleGenerateUrlDialog(generateUrlDialogOpen);
            return { generateUrlDialogOpen };
          }),
        setIsGenerateUrlSubmitting: (isGenerateUrlSubmitting: boolean) =>
          set({ isGenerateUrlSubmitting }),
        setGenerateUrl: (generateUrl: string | null) => set({ generateUrl }),
        setGenerateUrlError: (generateUrlError: string | null) =>
          set({ generateUrlError }),
      };
    },
    {
      name: "dashboard-store",
      partialize: (state: DashboardState) => ({
        userData: state.userData,
        projects: state.projects,
        selectedProjects: state.selectedProjects,
        isModalOpen: state.isModalOpen,
        modalType: state.modalType,
        expandedSections: state.expandedSections,
      }),
    },
  ),
);
