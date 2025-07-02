import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Project, ProjectCategories } from "../model/projectCategory";
import type { ChatMessage } from "../model/message";
import { fetchProjects } from "../lib/apiClient";
import { MARKDOWN_DIALOGUE_ID } from "../components/MarkdownDialogue";
import { ChatTypeOptions } from "../types/types";
import { ChatType } from "../lib/chatTypes";
import type { Topics } from "../model/topics";

type ChatStore = {
  jwt: string;
  projects?: ProjectCategories;
  chatMessages: ChatMessage[];
  isThinking: boolean;
  displayFloatingChatIntro: boolean;
  isMarkdownDialogueOpen: boolean;
  markdownDialogueContent: string;
  selectedProject?: Project | undefined;
  organisation_name: string;
  copiedMessageId: string | null;
  messagesEndRef: HTMLDivElement | null;
  chatType: ChatTypeOptions;
  topics: Topics | null,
  inputText: string,
  newProject: () => void;
  setJwt: (jwt: string) => void;
  setIsMarkdownDialogueOpen: (isOpen: boolean) => void;
  setMarkdownDialogueContent: (content: string) => void;
  logout: () => void;
  addChatMessage: (chatMessage: ChatMessage) => void;
  clearChatMessages: () => void;
  setProjects: (projects: ProjectCategories) => void;
  setSelectedProject: (project: Project | undefined) => void;
  initializeProjects: () => Promise<void>;
  setIsThinking: (isThinking: boolean) => void;
  setMessagesEndRef: (ref: HTMLDivElement | null) => void;
  scrollToBottom: () => void;
  setCopiedMessageId: (id: string) => void;
  setSelectedProjectAndChatType: (
    project: Project,
    chatType: ChatTypeOptions,
  ) => void;
  setChatType: (chatType: ChatTypeOptions) => void;
  refreshProjects: () => void;
  setTopics: (topics: Topics) => void;
  setInputText: (inputText: string) => void;
};

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
  const chatStore = localStorage.getItem("chat-store");
  if (!chatStore) {
    return "";
  }
  jwt = JSON.parse(chatStore).state.jwt;
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
    (
      document.getElementById(MARKDOWN_DIALOGUE_ID) as HTMLDialogElement
    )?.showModal();
  } else {
    (
      document.getElementById(MARKDOWN_DIALOGUE_ID) as HTMLDialogElement
    )?.close();
  }
}

const useChatStore = create<ChatStore>()(
  persist(
    (set, get) => {
      function loadInitialProjects(jwt: string) {
        if (jwt) {
          fetchProjects(jwt)
            .then((projects) => {
              set({ projects });
            })
            .catch((error) => {
              console.error("Error loading projects:", error);
            });
        }
      }

      // Initialize projects if JWT is available
      const initialJwt = initJwt();
      if (initialJwt) {
        loadInitialProjects(initialJwt);
      }

      return {
        jwt: initJwt(),
        projects: undefined,
        selectedProject: initProject(),
        chatMessages: [],
        isThinking: false,
        displayFloatingChatIntro:
          window.chatConfig?.displayFloatingChatIntro ?? false,
        isMarkdownDialogueOpen: false,
        markdownDialogueContent: "",
        copiedMessageId: null,
        messagesEndRef: null,
        chatType: ChatType.FULL_PAGE as ChatTypeOptions,
        organisation_name: window.chatConfig?.organisation_name ?? "Onepoint",
        topics: null,
        inputText: "",
        setJwt: (jwt: string) =>
          set(() => {
            if (jwt.length > 0) {
              loadInitialProjects(jwt);
            }
            return { jwt };
          }),
        setProjects: (projects: ProjectCategories) => set({ projects }),
        setSelectedProject: (project: Project | undefined) =>
          set(() => ({
              selectedProject: project,
              inputText: "",
              topics: null,
            })),
        setMessagesEndRef: (ref: HTMLDivElement | null) =>
          set({ messagesEndRef: ref }),

        addChatMessage: (message: ChatMessage) =>
          set((state) => {
            return {
              chatMessages: [
                ...state.chatMessages.slice(
                  state.chatMessages.length > THRESHOLD ? 1 : 0,
                ),
                message,
              ],
            };
          }),
        clearChatMessages: () =>
          set(() => {
            return { chatMessages: [], isThinking: false };
          }),
        // Logout completely
        logout: () =>
          set({
            jwt: "",
            projects: undefined,
            selectedProject: undefined,
            chatMessages: [],
            chatType: null,
            copiedMessageId: null,
            topics: null,
            inputText: "",
          }),
        newProject: () =>
          set({
            chatMessages: [],
            copiedMessageId: null,
            selectedProject: undefined,
            chatType: null,
          }),
        initializeProjects: async () => {
          const jwt = get().jwt;
          if (jwt) {
            const projects = await fetchProjects(jwt);
            set({ projects });
          }
        },
        scrollToBottom: () => {
          const messagesEndRef = get().messagesEndRef;
          if (messagesEndRef) {
            messagesEndRef.scrollIntoView({ behavior: "smooth" });
          }
        },
        setIsThinking: (isThinking: boolean) => set({ isThinking }),
        setIsMarkdownDialogueOpen: (isOpen: boolean) =>
          set(() => {
            openMarkdownDialogue(isOpen);
            return { isMarkdownDialogueOpen: isOpen };
          }),
        setMarkdownDialogueContent: (content: string) =>
          set(() => {
            openMarkdownDialogue(true);
            return { markdownDialogueContent: content };
          }),
        setCopiedMessageId: (id: string) => set({ copiedMessageId: id }),
        setSelectedProjectAndChatType: (selectedProject, chatType) =>
          set({ selectedProject, chatType }),
        setChatType: (chatType: ChatTypeOptions) => set({ chatType }),
        refreshProjects: () =>
          set((state) => {
            loadInitialProjects(state.jwt);
            return { ...state };
          }),
        setTopics: (topics: Topics) => set({ topics }),
        setInputText: (inputText: string) => set({ inputText }),
      };
    },
    {
      name: "chat-store",
      partialize: (state) => ({
        jwt: state.jwt,
        projects: state.projects,
        selectedProject: state.selectedProject,
        chatMessages: state.chatMessages,
        chatType: state.chatType,
        topics: state.topics,
      }),
    },
  ),
);

export default useChatStore;
