import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Project, ProjectCategories } from '../model/projectCategory';
import { fetchProjects } from '../lib/apiClient';

type ChatStore = {
    jwt: string;
    setJwt: (jwt: string) => void;
    projects?: ProjectCategories;
    setProjects: (projects: ProjectCategories) => void;
    selectedProject?: Project;
    setSelectedProject: (project: Project) => void;
    initializeProjects: () => Promise<void>;
}

function initJwt() {
    // Try to extract from location first
    const urlParams = new URLSearchParams(window.location.search);
    let jwt = urlParams.get("jwt");
    if (jwt) {
        return jwt;
    }
    // Try to extract from localStorage
    jwt = localStorage.getItem("jwt");
    if (jwt) {
        return jwt;
    }
    return "";
}

const useChatStore = create<ChatStore>()(
    persist(
        (set, get) => ({
            jwt: initJwt(),
            projects: undefined,
            selectedProject: undefined,
            setJwt: (jwt: string) => set({ jwt }),
            setProjects: (projects: ProjectCategories) => set({ projects }),
            setSelectedProject: (project: Project) => set({ selectedProject: project }),
            initializeProjects: async () => {
                const jwt = get().jwt
                if (jwt) {
                    const projects = await fetchProjects(jwt)
                    set({ projects })
                }
            }
        }),
        {
            name: "chat-store",
            partialize: (state) => ({
                jwt: state.jwt,
                projects: state.projects,
                selectedProject: state.selectedProject
            })
        }
    )
)

// Initialize projects after store creation
useChatStore.getState().initializeProjects();

export default useChatStore;