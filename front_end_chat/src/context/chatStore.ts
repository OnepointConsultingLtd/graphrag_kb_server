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
    displayFloatingChatIntro: boolean;
    isMarkdownDialogueOpen: boolean;
    markdownDialogueContent: string;
    selectedProject?: Project;
    copiedMessageId: string | null;
    messagesEndRef: HTMLDivElement | null;
    setJwt: (jwt: string) => void;
    setIsMarkdownDialogueOpen: (isOpen: boolean) => void;
    setMarkdownDialogueContent: (content: string) => void;
    logout: () => void;
    addChatMessage: (chatMessage: ChatMessage) => void;
    clearChatMessages: () => void;
    setProjects: (projects: ProjectCategories) => void;
    setSelectedProject: (project: Project) => void;
    setIsFloating: (isFloating: boolean) => void;
    initializeProjects: () => Promise<void>;
    setIsThinking: (isThinking: boolean) => void;
    setMessagesEndRef: (ref: HTMLDivElement | null) => void;
    scrollToBottom: () => void;
    setCopiedMessageId: (id: string) => void;
    newProject: (project: Project) => void;
}

const THRESHOLD = 50;

function initJwt() {
    // Try to extract from location first
    const urlParams = new URLSearchParams(window.location.search);
    let jwt = urlParams.get("token");
    if (jwt) {
        return jwt;
    }
    if (window.chatConfig?.jwt) {
        return window.chatConfig.jwt;
    }
    // Try to extract from localStorage
    jwt = localStorage.getItem("jwt");
    if (jwt) {
        return jwt;
    }
    return "";
}

function initProject() {
    const project = window.chatConfig?.project;
    if (project) {
        return project;
    }
    return undefined;
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
            selectedProject: initProject(),
            chatMessages: [],
            isFloating: false,
            isThinking: false,
            displayFloatingChatIntro: window.chatConfig?.displayFloatingChatIntro ?? false,
            isMarkdownDialogueOpen: false,
            markdownDialogueContent: "",
            copiedMessageId: null,
            messagesEndRef: null,
            setJwt: (jwt: string) => set({ jwt }),
            setProjects: (projects: ProjectCategories) => set({ projects }),
            setSelectedProject: (project: Project) => set({ selectedProject: project }),
            setIsFloating: (isFloating: boolean) => set({ isFloating }),
            setMessagesEndRef: (ref: HTMLDivElement | null) => set({ messagesEndRef: ref }),
            addChatMessage: (message: ChatMessage) => set((state) => {
                return { chatMessages: [...state.chatMessages.slice(state.chatMessages.length > THRESHOLD ? 1 : 0), message] }
            }),
            clearChatMessages: () => set(() => {
                return { chatMessages: [], isThinking: false }
            }),
            // Logout completely
            logout: () => set({
                jwt: "",
                projects: undefined,
                selectedProject: undefined,
                chatMessages: [],
                copiedMessageId: null
            }),
            // Switch to a new project while keeping the user logged in
            newProject: (project: Project) => set({
                projects: undefined,
                chatMessages: [],
                copiedMessageId: null,
                selectedProject: project
            }),
            initializeProjects: async () => {
                const jwt = get().jwt
                if (jwt) {
                    const projects = await fetchProjects(jwt)
                    set({ projects })
                }
            },
            scrollToBottom: () => {
                const messagesEndRef = get().messagesEndRef;
                if (messagesEndRef) {
                    messagesEndRef.scrollIntoView({ behavior: "smooth" });
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
            })
        }
    )
);

// Initialize projects after store creation
useChatStore.getState().initializeProjects();

export default useChatStore;