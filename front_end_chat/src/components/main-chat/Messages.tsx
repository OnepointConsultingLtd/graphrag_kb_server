import { useEffect, useState } from "react";
import { GiCardJoker } from "react-icons/gi";
import { useShallow } from "zustand/react/shallow";
import { SCROLL_TO_BOTTOM_ID } from "../../constants/scroll";
import useChatStore from "../../context/chatStore";
import useWebsocket from "../../hooks/useWebsocket";
import { fetchTopics } from "../../lib/apiClient";
import { ChatType } from "../../lib/chatTypes";
import { ChatMessage, ChatMessageTypeOptions } from "../../model/message";
import { Topic } from "../../model/topics";
import { ChatTypeOptions } from "../../model/types";
import ReferenceDisplay from "../messages/ReferenceDisplay";
import RenderReactMarkdown from "./RenderReactMarkdown";
import ThinkingIndicator from "./ThinkingIndicator";
import { ButtonLayout } from "../buttons/ButtonLayout";
import TopicButtons from "../buttons/TopicButtons";
import { useDashboardStore } from "../../context/dashboardStore";
import Spinner from "../icons/Spinner";
import { Reference } from "../../model/references";
import { Project } from "../../model/projectCategory";

export function topicQuestionTemplate(topic: Topic) {
  return `Tell me more about this topic: ${topic.name}`;
}

function JokerButton() {
  const { topics, setInputText, chatType } = useChatStore(
    useShallow((state) => ({
      topics: state.topics,
      setInputText: state.setInputText,
      chatType: state.chatType,
    })),
  );

  function hasTopics() {
    return topics && topics.topics && topics.topics.length > 0;
  }

  if (!hasTopics()) {
    return null;
  }

  function handleClick(e: React.MouseEvent<HTMLButtonElement>) {
    e.preventDefault();
    e.stopPropagation();
    if (!hasTopics()) {
      return;
    }
    const randomTopic =
      topics?.topics[Math.floor(Math.random() * topics.topics.length)];
    if (randomTopic) {
      setInputText(topicQuestionTemplate(randomTopic));
    }
  }

  const isFloating = chatType === ChatType.FLOATING;

  return (
    <button
      className={`w-11 h-11 -mt-1 cursor-pointer ${!isFloating ? "tooltip" : ""}`}
      data-tip="Click for random topic"
      title={`${isFloating ? "Click for random topic" : ""}`}
      onClick={handleClick}
    >
      <GiCardJoker className="h-12 w-12 bg-[#0992C2] border-[#0992C2] rounded-sm text-white" />
    </button>
  );
}

const INCREMENT_TOPICS_NUMBER = 4;

export const INCREMENT_TOPICS_BUTTON_ID = "increment-topics-button";

function ConversationTopicCommandButtons() {
  const { conversationTopicsNumber, setConversationTopicsNumber } =
    useChatStore(
      useShallow((state) => ({
        conversationTopicsNumber: state.conversationTopicsNumber,
        setConversationTopicsNumber: state.setConversationTopicsNumber,
      })),
    );

  return (
    <div className="flex flex-row gap-2 justify-between mt-2">
      <div className="flex flex-row gap-2">
        {conversationTopicsNumber > INCREMENT_TOPICS_NUMBER && (
          <button
            className="btn btn-neutral bg-[#0992C2] border-[#0992C2]"
            onClick={() =>
              setConversationTopicsNumber(
                conversationTopicsNumber - INCREMENT_TOPICS_NUMBER,
              )
            }
            title="Display less topics"
          >
            -
          </button>
        )}

        <button
          className="btn btn-neutral bg-[#0992C2] border-[#0992C2]"
          id={INCREMENT_TOPICS_BUTTON_ID}
          onClick={() =>
            setConversationTopicsNumber(
              conversationTopicsNumber + INCREMENT_TOPICS_NUMBER,
            )
          }
          title="Display more topics"
        >
          +
        </button>
      </div>
      <JokerButton />
    </div>
  );
}

function ConversationTopics() {
  const { downloadingTopics, setDownloadingTopics } = useDashboardStore();
  const {
    jwt,
    selectedProject,
    topics,
    conversationTopicsNumber,
    chatType,
    showTopics,
    setTopics,
  } = useChatStore(
    useShallow((state) => ({
      jwt: state.jwt,
      selectedProject: state.selectedProject,
      topics: state.topics,
      conversationTopicsNumber: state.conversationTopicsNumber,
      chatType: state.chatType,
      selectedTopic: state.selectedTopic,
      showTopics: state.showTopics,
      setSelectedTopic: state.setSelectedTopic,
      setTopics: state.setTopics,
      setInputText: state.setInputText,
    })),
  );

  useEffect(() => {
    if (jwt && selectedProject) {
      setDownloadingTopics(true);
      fetchTopics(jwt, selectedProject, conversationTopicsNumber)
        .then(setTopics)
        .then(() => {
          document.getElementById(INCREMENT_TOPICS_BUTTON_ID)?.scrollIntoView({
            behavior: "smooth",
            block: "start", // options: 'start', 'center', 'end', 'nearest'
          });
        })
        .catch(console.error)
        .finally(() => setDownloadingTopics(false));
    }
  }, [jwt, selectedProject, setTopics, conversationTopicsNumber]);

  if (!selectedProject) {
    return null;
  }

  const hasTopics = topics && topics.topics.length > 0;

  if (selectedProject && !showTopics) {
    return null;
  }

  const isFloating = chatType === ChatType.FLOATING;

  return (
    <div
      className={`flex-1 flex items-center justify-center text-gray-500 ${isFloating ? "mt-0" : "mt-12"}`}
    >
      <div className="w-full text-center">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="lucide lucide-message-circle w-12 h-12 mx-auto mb-3 text-gray-300"
        >
          <path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"></path>
        </svg>
        {!hasTopics && !downloadingTopics && <p>Start a conversation...</p>}
        {downloadingTopics && (
          <div className="flex justify-center items-center pt-4">
            <div>
              <Spinner size={12} />
              <p>Downloading topics...</p>
            </div>
          </div>
        )}
        {hasTopics && (
          <p className="mb-6">Select a topic for a conversation...</p>
        )}
        {(hasTopics || showTopics) && (
          <ButtonLayout>
            <TopicButtons topics={topics} related={false} />
          </ButtonLayout>
        )}
        {hasTopics && showTopics && <ConversationTopicCommandButtons />}
      </div>
    </div>
  );
}

export function TopicSwitcher() {
  const { showTopics, chatMessages, chatType, isThinking, setShowTopics } =
    useChatStore(
      useShallow((state) => ({
        showTopics: state.showTopics,
        chatMessages: state.chatMessages,
        chatType: state.chatType,
        isThinking: state.isThinking,
        setShowTopics: state.setShowTopics,
      })),
    );

  if (isThinking || chatMessages.length === 0) {
    return null;
  }

  const isFloating = chatType === ChatType.FLOATING;

  const title = showTopics ? "Hide topics" : "Show topics";

  return (
    <div className="flex flex-row gap-2 justify-end -mt-2">
      <button
        className={`w-5 h-5 filter brightness-150 cursor-pointer mr-3 ${!isFloating ? "tooltip" : ""}`}
        data-tip={title}
        title={title}
        onClick={() => setShowTopics(!showTopics)}
      >
        <svg
          strokeWidth="0"
          fill={isFloating ? "#6a7282" : "white"}
          viewBox="0 0 1024 1024"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path d="M912 192H328c-4.4 0-8 3.6-8 8v56c0 4.4 3.6 8 8 8h584c4.4 0 8-3.6 8-8v-56c0-4.4-3.6-8-8-8zm0 284H328c-4.4 0-8 3.6-8 8v56c0 4.4 3.6 8 8 8h584c4.4 0 8-3.6 8-8v-56c0-4.4-3.6-8-8-8zm0 284H328c-4.4 0-8 3.6-8 8v56c0 4.4 3.6 8 8 8h584c4.4 0 8-3.6 8-8v-56c0-4.4-3.6-8-8-8zM104 228a56 56 0 1 0 112 0 56 56 0 1 0-112 0zm0 284a56 56 0 1 0 112 0 56 56 0 1 0-112 0zm0 284a56 56 0 1 0 112 0 56 56 0 1 0-112 0z"></path>
        </svg>
      </button>
    </div>
  );
}

export function SingleMessage({ message, index, selectedProject, chatMessages, isFloating }: { 
  message: ChatMessage, index: number, selectedProject: Project | undefined, chatMessages: ChatMessage[], isFloating: boolean 
}) {
  if (!selectedProject) {
    return null;
  }

  const [availableReferences, setAvailableReferences] = useState<Reference[]>([]);

  useEffect(() => {
    setAvailableReferences(message.references || []);
  }, [message]);

  return (
    <div
      key={message.id}
      className={`flex ${
        message.type === ChatMessageTypeOptions.USER
          ? "justify-end"
          : "justify-start"
      } animate-slideIn items-start`}
    >
      <div
        className={`text-left ${
          isFloating ? "p-2" : "p-6"
        } relative max-w-full rounded-lg rounded-tr-sm ${
          message.type === ChatMessageTypeOptions.USER
            ? isFloating
              ? "bg-[#0992C2] md:max-w-[70%] shadow-lg text-white"
              : "bg-gradient-to-br from-sky-500 to-blue-500 md:max-w-[50%] shadow-lg text-white"
            : isFloating
              ? "bg-white text-slate-800 rounded-2xl rounded-tl-sm w-full border border-purple-100"
              : "bg-white text-slate-800 rounded-2xl rounded-tl-sm md:!max-w-[70%] border border-sky-100"
        }`}
      >
        {index === chatMessages.length - 1 && (
          <div id={SCROLL_TO_BOTTOM_ID} />
        )}
        <RenderReactMarkdown message={message} />
        {availableReferences?.length &&
        availableReferences.length > 0 ? (
          <ul className="mt-2">
            {availableReferences.map((reference) => (
              <ReferenceDisplay
                key={reference.url}
                reference={reference}
              />
            ))}
          </ul>
        ) : null}
      </div>
    </div>
  )
}

export default function Messages() {

  
  const {
    selectedProject,
    chatMessages,
    chatType,
    setChatType,
    isThinking,
    scrollToBottom,
    relatedTopics,
    loadingRelatedTopics,
  } = useChatStore(
    useShallow((state) => ({
      selectedProject: state.selectedProject,
      chatMessages: state.chatMessages,
      chatType: state.chatType,
      showTopics: state.showTopics,
      setChatType: state.setChatType,
      isThinking: state.isThinking,
      scrollToBottom: state.scrollToBottom,
      relatedTopics: state.relatedTopics,
      loadingRelatedTopics: state.loadingRelatedTopics,
    })),
  );

  useWebsocket();

  useEffect(() => {
    setChatType(ChatType.FULL_PAGE as ChatTypeOptions);
  }, [setChatType]);

  useEffect(() => {
    scrollToBottom();
  }, [scrollToBottom]);

  useEffect(() => {
    if (isThinking) {
      scrollToBottom();
    }
  }, [chatMessages, isThinking, scrollToBottom]);

  const isFloating = chatType === ChatType.FLOATING;

  return (
    <div className="flex-1 flex-col">
      <div>
        <div className="mx-auto">
          <div
            className={`flex flex-col gap-6 ${
              isFloating ? "p-1 pt-8" : "p-2 lg:p-6"
            }`}
          >
            {chatMessages.map((message, index) => {
              return <SingleMessage key={message.id} message={message} index={index} selectedProject={selectedProject} chatMessages={chatMessages} isFloating={isFloating} />;
            })}
            <ConversationTopics />
            <TopicSwitcher />
            {loadingRelatedTopics && (
              <div className="skeleton h-32 w-full"></div>
            )}
            {relatedTopics && !loadingRelatedTopics && (
              <>
                <h3
                  className={`text-lg font-bold ${isFloating ? "text-gray-500" : ""}`}
                >
                  Related Topics
                </h3>
                <ButtonLayout>
                  <TopicButtons topics={relatedTopics} related={true} />
                </ButtonLayout>
              </>
            )}
            {/* Thinking Indicator */}
            {isThinking && <ThinkingIndicator />}
          </div>
        </div>
      </div>
    </div>
  );
}
