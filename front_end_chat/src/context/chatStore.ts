import { create } from "zustand";
import { persist } from "zustand/middleware";
import type {
  Platform,
  Project,
  ProjectCategories,
  SearchType,
} from "../model/projectCategory";
import { ENGINES } from "../constants/engines";
import { type ChatMessage, ChatMessageTypeOptions } from "../model/message";
import { fetchProjects, fetchRelatedTopics } from "../lib/apiClient";
import { MARKDOWN_DIALOGUE_ID } from "../components/MarkdownDialogue";
import { ChatTypeOptions } from "../model/types";
import { ChatType } from "../lib/chatTypes";
import type { Topic, Topics } from "../model/topics";
import { io, type Socket } from "socket.io-client";
import { getWebsocketServer } from "../lib/server";
import { createChatMessage } from "../factory/chatMessageFactory";
import { SCROLL_TO_BOTTOM_ID } from "../constants/scroll";
import {
  getDisplayFloatingChatIntro,
  getOrganisationName,
  getParameter,
  getParameterFromUrl,
} from "../lib/parameters";
import { showCloseModal } from "../lib/dialog";
import { topicQuestionTemplate } from "../components/main-chat/Messages";
import { v4 as uuidv4 } from "uuid";

if (getParameterFromUrl("token")) {
  localStorage.removeItem("chat-store");
}

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
  chatType: ChatTypeOptions;
  topics: Topics | null;
  inputText: string;
  selectedTopic: Topic | null;
  relatedTopics: Topics | null;
  loadingRelatedTopics: boolean;
  conversationId: string | null;
  socket: Socket<any, any> | null;
  useStreaming: boolean;
  conversationTopicsNumber: number;
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
  scrollToBottom: () => void;
  setCopiedMessageId: (id: string) => void;
  setSelectedProjectAndChatType: (
    project: Project,
    chatType: ChatTypeOptions,
  ) => void;
  setChatType: (chatType: ChatTypeOptions) => void;
  refreshProjects: () => void;
  setTopics: (topics: Topics) => void;
  injectTopicDescription: (index: number, related: boolean) => void;
  setInputText: (inputText: string) => void;
  setSelectedTopic: (topic: Topic) => void;
  setConversationId: (conversationId: string) => void;
  setUseStreaming: (useStreaming: boolean) => void;
  setConversationTopicsNumber: (conversationTopicsNumber: number) => void;
  setShowTopics: (showTopics: boolean) => void;
  streamEnded: () => void;
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
  return getParameter("token");
}

function initChatType(): ChatTypeOptions {
  const chatType = getParameterFromUrl("chat_type");
  if (chatType) {
    return chatType as ChatTypeOptions;
  }
  const widgetType = window.chatConfig?.widgetType;
  if (widgetType) {
    return (
      widgetType === "FLOATING_CHAT" ? ChatType.FLOATING : ChatType.FULL_PAGE
    ) as ChatTypeOptions;
  }
  return null;
}

function initProject(): Project | undefined {
  const projectName = getParameterFromUrl("project");
  const platform = getParameterFromUrl("platform");
  const search_type = getParameterFromUrl("search_type");
  const additional_prompt_instructions =
    getParameterFromUrl("additional_prompt_instructions") ?? "";
  if (projectName && platform && search_type) {
    const project = {
      name: projectName,
      updated_timestamp: new Date(),
      input_files: [],
      search_type: search_type as SearchType,
      platform: platform as Platform,
      additional_prompt_instructions,
    };
    console.info("project", project);
    return project as Project;
  }
  const project = window.chatConfig?.project;
  if (project) {
    return project as Project;
  }
  return undefined;
}

function openMarkdownDialogue(open: boolean) {
  showCloseModal(open, MARKDOWN_DIALOGUE_ID);
}

function initStreaming(): boolean {
  const streaming = getParameter("streaming");
  if (streaming) {
    return streaming === "true";
  }
  return false;
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

      function loadRelatedTopics(message: ChatMessage) {
        const isAgentMessage = message.type === ChatMessageTypeOptions.AGENT
        if (!isAgentMessage) {
          return;
        }
        const state = get();
        const text = state.chatMessages.slice(-1)[0].text;
        const selectedTopic = state.selectedTopic?.name ?? "";
        if (
          state.selectedProject &&
          state.selectedProject?.platform !== ENGINES.CAG &&
          (text || selectedTopic)
        ) {
          set({ loadingRelatedTopics: true });
          fetchRelatedTopics(
            state.jwt,
            state.selectedProject,
            8,
            selectedTopic,
            text,
          )
            .then((relatedTopics) => {
              set({ relatedTopics });
            })
            .catch((error) => {
              console.error("Error fetching related topics:", error);
              set({ relatedTopics: null });
            })
            .finally(() => {
              set({ loadingRelatedTopics: false, selectedTopic: null });
            });
        } else {
          set({ relatedTopics: null, selectedTopic: null });
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
        displayFloatingChatIntro: getDisplayFloatingChatIntro(),
        isMarkdownDialogueOpen: false,
        markdownDialogueContent: "",
        copiedMessageId: null,
        messagesEndRef: null,
        chatType: initChatType(),
        organisation_name: getOrganisationName(),
        topics: null,
        inputText: "",
        selectedTopic: null,
        loadingRelatedTopics: false,
        conversationId: null,
        socket: initSocket(),
        useStreaming: initStreaming(),
        conversationTopicsNumber: 6,
        showTopics: true,
        relatedTopics: null,
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
            relatedTopics: null,
          })),
        addChatMessage: (message: ChatMessage) =>
          set((state) => {
            loadRelatedTopics(message);
            return {
              chatMessages: [
                ...state.chatMessages.slice(
                  state.chatMessages.length > THRESHOLD ? 1 : 0,
                ),
                message,
              ],
              showTopics: false,
              relatedTopics: null,
            };
          }),
        appendToLastChatMessage: (token: string) =>
          set((state) => {
            const lastMessage = state.chatMessages.slice(-1)[0];
            if (lastMessage.type === ChatMessageTypeOptions.USER) {
              return {
                chatMessages: [
                  ...state.chatMessages,
                  createChatMessage(token, state.conversationId),
                ],
                isThinking: false,
                showTopics: false,
              };
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
              conversationId: uuidv4(),
              showTopics: true,
              relatedTopics: null,
              selectedTopic: null,
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
            relatedTopics: null,
            selectedTopic: null,
          }),
        newProject: () =>
          set(() => {
            return {
              chatMessages: [],
              copiedMessageId: null,
              selectedProject: undefined,
              chatType: null,
              showTopics: false,
              relatedTopics: null,
              selectedTopic: null,
              inputText: "",
            }
          }),
        initializeProjects: async () => {
          const jwt = get().jwt;
          if (jwt) {
            const projects = await fetchProjects(jwt);
            set({ projects });
          }
        },
        scrollToBottom: () => {
          document.getElementById(SCROLL_TO_BOTTOM_ID)?.scrollIntoView({
            behavior: "smooth",
            block: "start", // options: 'start', 'center', 'end', 'nearest'
          });
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
            conversationId: uuidv4(),
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
        setTopics: (topics: Topics) =>
          set(() => {
            const filteredTopics = topics?.topics?.filter((topic) => topic.type);
            return {
              topics: { topics: filteredTopics },
              conversationTopicsNumber: topics?.topics?.length ?? 0,
            };
          }),
        injectTopicDescription: (index: number, related: boolean) =>
          set((state) => {
            const currentTopics = related ? state.relatedTopics?.topics : state.topics?.topics
            if (!currentTopics) {
              return related ? { relatedTopics: { topics: [] } } : { topics: { topics: [] } };
            }
            const newTopics = currentTopics.filter((topic) => topic.type).map((topic, i) => ({...topic, showDescription: i === index ? (topic.showDescription ? false : true) : false }))
            return related ? { relatedTopics: { topics: newTopics } } : { topics: { topics: newTopics } };
          }),
        setInputText: (inputText: string) =>
          set((_) => {
            return { inputText };
          }),
        setSelectedTopic: (topic: Topic) =>
          set((state) => {
            const selected = state.selectedTopic?.name === topic.name;
            return {
              selectedTopic: selected ? null : topic,
              inputText: selected ? "" : topicQuestionTemplate(topic),
            };
          }),
        setConversationId: (conversationId: string) => set({ conversationId }),
        setUseStreaming: (useStreaming: boolean) => set({ useStreaming }),
        setConversationTopicsNumber: (conversationTopicsNumber: number) =>
          set({ conversationTopicsNumber }),
        setShowTopics: (showTopics: boolean) =>
          set(() => {
            return { showTopics };
          }),
        streamEnded: () =>
          set(() => {
            const state = get();
            state.scrollToBottom();
            if (state.chatMessages.length > 0) {
              loadRelatedTopics(state.chatMessages.slice(-1)[0]);
            }
            return { isThinking: false };
          }),
      };
    },
    {
      name: "chat-store",
      partialize: (state) => ({
        jwt: state.jwt,
        projects: state.projects,
        selectedProject: state.selectedProject,
        chatMessages: state.chatMessages,
        topics: state.topics,
        useStreaming: state.useStreaming,
        relatedTopics: state.relatedTopics,
      }),
    },
  ),
);

export default useChatStore;
