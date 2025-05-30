import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Project, ProjectCategories } from '../model/projectCategory';
import type { ChatMessage } from '../model/message';
import { fetchProjects } from '../lib/apiClient';

type ChatStore = {
    jwt: string;
    setJwt: (jwt: string) => void;
    projects?: ProjectCategories;
    chatMessages: ChatMessage[];
    isFloating: boolean;
    isThinking: boolean;
    logout: () => void;
    addChatMessage: (chatMessage: ChatMessage) => void;
    clearChatMessages: () => void;
    setProjects: (projects: ProjectCategories) => void;
    selectedProject?: Project;
    setSelectedProject: (project: Project) => void;
    initializeProjects: () => Promise<void>;
    setIsThinking: (isThinking: boolean) => void;
}

const THRESHOLD = 50;

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
            chatMessages: [],
            isFloating: false, // TODO: create initialisation function
            isThinking: false,
            setJwt: (jwt: string) => set({ jwt }),
            setProjects: (projects: ProjectCategories) => set({ projects }),
            setSelectedProject: (project: Project) => set({ selectedProject: project }),
            addChatMessage: (message: ChatMessage) => set((state) => {
                return { chatMessages: [...state.chatMessages.slice(state.chatMessages.length > THRESHOLD ? 1 : 0), message] }
            }),
            clearChatMessages: () => set(() => {
                return { chatMessages: [], isThinking: false }
            }),
            logout: () => set({ jwt: "", projects: undefined, selectedProject: undefined, chatMessages: [] }),
            initializeProjects: async () => {
                const jwt = get().jwt
                if (jwt) {
                    const projects = await fetchProjects(jwt)
                    set({ projects })
                }
            },
            setIsThinking: (isThinking: boolean) => set({ isThinking })
        }),
        {
            name: "chat-store",
            partialize: (state) => ({
                jwt: state.jwt,
                projects: state.projects,
                selectedProject: state.selectedProject,
                chatMessages: state.chatMessages
            })
        }
    )
)

// Initialize projects after store creation
useChatStore.getState().initializeProjects();

export default useChatStore;