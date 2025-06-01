import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Project, ProjectCategories } from '../model/projectCategory';
import type { ChatMessage } from '../model/message';
import { fetchProjects } from '../lib/apiClient';
import { MARKDOWN_DIALOGUE_ID } from '../components/MarkdownDialogue';

type ChatStore = {
    jwt: string;
    projects?: ProjectCategories;
    chatMessages: ChatMessage[];
    isFloating: boolean;
    isThinking: boolean;
    isMarkdownDialogueOpen: boolean;
    markdownDialogueContent: string;
    selectedProject?: Project;
    copiedMessageId: string | null;
    setJwt: (jwt: string) => void;
    setIsMarkdownDialogueOpen: (isOpen: boolean) => void;
    setMarkdownDialogueContent: (content: string) => void;
    logout: () => void;
    addChatMessage: (chatMessage: ChatMessage) => void;
    clearChatMessages: () => void;
    setProjects: (projects: ProjectCategories) => void;
    setSelectedProject: (project: Project) => void;
    initializeProjects: () => Promise<void>;
    setIsThinking: (isThinking: boolean) => void;
    setCopiedMessageId: (id: string) => void;
}

const THRESHOLD = 50;

function initJwt() {
    // Try to extract from location first
    const urlParams = new URLSearchParams(window.location.search);
    let jwt = urlParams.get("token");
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

function openMarkdownDialogue(open: boolean) {
    if (open) {
        (document.getElementById(MARKDOWN_DIALOGUE_ID) as HTMLDialogElement)?.showModal();
    } else {
        (document.getElementById(MARKDOWN_DIALOGUE_ID) as HTMLDialogElement)?.close();
    }
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
            isMarkdownDialogueOpen: false,
            markdownDialogueContent: "",
            copiedMessageId: null,
            setJwt: (jwt: string) => set({ jwt }),
            setProjects: (projects: ProjectCategories) => set({ projects }),
            setSelectedProject: (project: Project) => set({ selectedProject: project }),
            addChatMessage: (message: ChatMessage) => set((state) => {
                return { chatMessages: [...state.chatMessages.slice(state.chatMessages.length > THRESHOLD ? 1 : 0), message] }
            }),
            clearChatMessages: () => set(() => {
                return { chatMessages: [], isThinking: false }
            }),
            logout: () => set({ 
                jwt: "",
                projects: undefined, 
                selectedProject: undefined, 
                chatMessages: [],
                copiedMessageId: null
            }),
            initializeProjects: async () => {
                const jwt = get().jwt
                if (jwt) {
                    const projects = await fetchProjects(jwt)
                    set({ projects })
                }
            },
            setIsThinking: (isThinking: boolean) => set({ isThinking }),
            setIsMarkdownDialogueOpen: (isOpen: boolean) => set(() => {
                openMarkdownDialogue(isOpen);
                return { isMarkdownDialogueOpen: isOpen }
            }),
            setMarkdownDialogueContent: (content: string) => set(() => {
                openMarkdownDialogue(true);
                return { markdownDialogueContent: content }
            }),
            setCopiedMessageId: (id: string) => set({ copiedMessageId: id })
        }),
        {
            name: "chat-store",
            partialize: (state) => ({
                jwt: state.jwt,
                projects: state.projects,
                selectedProject: state.selectedProject,
                chatMessages: state.chatMessages
            }),
            onRehydrateStorage: () => (state, error) => {
                if (error) {
                    console.error("Error during hydration", error);
                }

                // If no jwt was found in storage, call initJwt() to set a default
                if (!state?.jwt) {
                    const defaultJwt = initJwt();
                    state?.setJwt(defaultJwt);
                }
            },
        }
    )
)

// Initialize projects after store creation
useChatStore.getState().initializeProjects();

export default useChatStore;