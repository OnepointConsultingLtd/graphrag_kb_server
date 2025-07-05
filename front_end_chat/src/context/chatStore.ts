import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Project, ProjectCategories } from "../model/projectCategory";
import { type ChatMessage, ChatMessageTypeOptions } from "../model/message";
import { fetchProjects } from "../lib/apiClient";
import { MARKDOWN_DIALOGUE_ID } from "../components/MarkdownDialogue";
import { ChatTypeOptions } from "../model/types";
import { ChatType } from "../lib/chatTypes";
import type { Topics } from "../model/topics";
import { io, type Socket } from "socket.io-client";
import { getWebsocketServer } from "../lib/server";
import { createChatMessage } from "../factory/chatMessageFactory";

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
  topics: Topics | null;
  inputText: string;
  conversationId: string | null;
  socket: Socket<any, any> | null;
  useStreaming: boolean;
  conversationTopicsNumber: number
  showTopics: boolean;
  newProject: () => void;
  setJwt: (jwt: string) => void;
  setIsMarkdownDialogueOpen: (isOpen: boolean) => void;
  setMarkdownDialogueContent: (content: string) => void;
  logout: () => void;
  addChatMessage: (chatMessage: ChatMessage) => void;
  appendToLastChatMessage: (token: string) => void;
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
  setConversationId: (conversationId: string) => void;
  setUseStreaming: (useStreaming: boolean) => void;
  setConversationTopicsNumber: (conversationTopicsNumber: number) => void;
  setShowTopics: (showTopics: boolean) => void;
};

const THRESHOLD = 50;

function initSocket() {
  const socket = io(getWebsocketServer(), {
    transports: ["websocket"],
    autoConnect: true,
  });
  return socket;
}

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
        conversationId: null,
        socket: initSocket(),
        useStreaming: false,
        conversationTopicsNumber: 6,
        showTopics: false,
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
              showTopics: false,
            };
          }),
        appendToLastChatMessage: (token: string) =>
          set((state) => {
            const lastMessage = state.chatMessages.slice(-1)[0];
            if(lastMessage.type === ChatMessageTypeOptions.USER) {
              return {
                chatMessages: [...state.chatMessages, createChatMessage(token, state.conversationId)],
                isThinking: false,
                showTopics: false,
              }
            }
            lastMessage.text += token;
            return {
              chatMessages: [...state.chatMessages.slice(0, -1), lastMessage],
              showTopics: false,
            };
          }),
        clearChatMessages: () =>
          set(() => {
            return {
              chatMessages: [],
              isThinking: false,
              conversationId: crypto.randomUUID(),
              showTopics: true,
            };
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
            useStreaming: false,
            showTopics: false,
          }),
        newProject: () =>
          set({
            chatMessages: [],
            copiedMessageId: null,
            selectedProject: undefined,
            chatType: null,
            showTopics: false,
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
          set({
            selectedProject,
            chatType,
            conversationId: crypto.randomUUID(),
            chatMessages: [],
            isThinking: false,
            conversationTopicsNumber: chatType === ChatType.FLOATING ? 6 : 12,
            showTopics: true,
          }),
        setChatType: (chatType: ChatTypeOptions) => set({ chatType }),
        refreshProjects: () =>
          set((state) => {
            loadInitialProjects(state.jwt);
            return { ...state };
          }),
        setTopics: (topics: Topics) => set(() => {
          return { topics, conversationTopicsNumber: topics?.topics?.length ?? 0 }
        }),
        setInputText: (inputText: string) => set({ inputText }),
        setConversationId: (conversationId: string) => set({ conversationId }),
        setUseStreaming: (useStreaming: boolean) => set({ useStreaming }),
        setConversationTopicsNumber: (conversationTopicsNumber: number) => set({ conversationTopicsNumber }),
        setShowTopics: (showTopics: boolean) => set({ showTopics }),
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
        useStreaming: state.useStreaming,
      }),
    },
  ),
);

export default useChatStore;
