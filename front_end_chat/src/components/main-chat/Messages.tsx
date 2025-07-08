import { useEffect } from "react";
import { GiCardJoker } from "react-icons/gi";
import { useShallow } from "zustand/react/shallow";
import { SCROLL_TO_BOTTOM_ID } from "../../constants/scroll";
import useChatStore from "../../context/chatStore";
import useWebsocket from "../../hooks/useWebsocket";
import { fetchTopics } from "../../lib/apiClient";
import { ChatType } from "../../lib/chatTypes";
import { ChatMessageTypeOptions } from "../../model/message";
import { Topic } from "../../model/topics";
import { ChatTypeOptions } from "../../model/types";
import ReferenceDisplay from "../messages/ReferenceDisplay";
import RenderReactMarkdown from "./RenderReactMarkdown";
import ThinkingIndicator from "./ThinkingIndicator";

function simplifyDescription(description: string) {
  if (!description) {
    return "";
  }
  return description.split("<SEP>")[0].split(".")[0].substring(0, 100) + " ...";
}

function topicQuestionTemplate(topic: Topic) {
  return `Tell me more about this topic: ${topic.name}`;
}

function JokerButton() {
  const { topics, setInputText, chatType } = useChatStore(
    useShallow((state) => ({
      topics: state.topics,
      setInputText: state.setInputText,
      chatType: state.chatType,
    }))
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
      className={`w-11 h-11 -mt-1 cursor-pointer filter hue-rotate-120 saturate-200 brightness-155 ${!isFloating ? "tooltip" : ""}`}
      data-tip="Click for random topic"
      title={`${isFloating ? "Click for random topic" : ""}`}
      onClick={handleClick}
    >
      <GiCardJoker className="text-7xl" />
    </button>
  );
}

const INCREMENT_TOPICS_NUMBER = 4;

export const INCREMENT_TOPICS_BUTTON_ID = "increment-topics-button";

function ConversationTopics() {
  const {
    jwt,
    selectedProject,
    topics,
    conversationTopicsNumber,
    setTopics,
    chatType,
    setInputText,
    setConversationTopicsNumber,
    showTopics,
  } = useChatStore(
    useShallow((state) => ({
      jwt: state.jwt,
      selectedProject: state.selectedProject,
      topics: state.topics,
      conversationTopicsNumber: state.conversationTopicsNumber,
      chatType: state.chatType,
      setTopics: state.setTopics,
      setInputText: state.setInputText,
      setConversationTopicsNumber: state.setConversationTopicsNumber,
      showTopics: state.showTopics,
    }))
  );

  useEffect(() => {
    if (jwt && selectedProject) {
      fetchTopics(jwt, selectedProject, conversationTopicsNumber)
        .then(setTopics)
        .then(() => {
          document.getElementById(INCREMENT_TOPICS_BUTTON_ID)?.scrollIntoView({
            behavior: "smooth",
            block: "start", // options: 'start', 'center', 'end', 'nearest'
          });
        })
        .catch(console.error);
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
        {!hasTopics && <p>Start a conversation...</p>}
        {hasTopics && (
          <p className="mb-6">Select a topic for a conversation...</p>
        )}
        {(hasTopics || showTopics) && (
          <div
            className={`grid overflow-x-hidden grid-cols-1 lg:grid-cols-${chatType === ChatType.FLOATING ? 2 : 4} md:grid-cols-2 w-full gap-3`}
          >
            {topics?.topics.filter((topic) => topic.type).map((topic) => (
              <div
                className={`flex flex-col items-left justify-top text-left cursor-pointer bg-[var(--color-primary)] hover:bg-[var(--color-accent-content)] p-2 rounded-lg`}
                key={`topic-${topic.name}-${topic.type}`}
                onClick={() => setInputText(topicQuestionTemplate(topic))}
                title={isFloating ? topic.description : ""}
              >
                <div className="flex flex-row justify-between gap-2">
                  <div className="text-white font-bold">{topic.name}</div>
                  {!isFloating &&<div className="text-white">{topic.type}</div>}
                </div>
                <div className="w-full text-white text-sm">{simplifyDescription(topic.description)}</div>
              </div>
            ))}
          </div>
        )}
        {(hasTopics && showTopics) && (
          <div className="flex flex-row gap-2 justify-between mt-2">
            <div className="flex flex-row gap-2">
              {conversationTopicsNumber > INCREMENT_TOPICS_NUMBER && (
                <button
                  className="btn btn-secondary"
                  onClick={() =>
                    setConversationTopicsNumber(
                      conversationTopicsNumber - INCREMENT_TOPICS_NUMBER
                    )
                  }
                  title="Display less topics"
                >
                  -
                </button>
              )}

              <button
                className="btn btn-success"
                id={INCREMENT_TOPICS_BUTTON_ID}
                onClick={() =>
                  setConversationTopicsNumber(
                    conversationTopicsNumber + INCREMENT_TOPICS_NUMBER
                  )
                }
                title="Display more topics"
              >
                +
              </button>
            </div>
            <JokerButton />
          </div>
        )}
      </div>
    </div>
  );
}

export function TopicSwitcher() {
  const {
    showTopics,
    chatMessages,
    chatType,
    isThinking,
    setShowTopics,
    scrollToBottom,
  } = useChatStore(
    useShallow((state) => ({
      showTopics: state.showTopics,
      chatMessages: state.chatMessages,
      chatType: state.chatType,
      isThinking: state.isThinking,
      setShowTopics: state.setShowTopics,
      scrollToBottom: state.scrollToBottom,
    }))
  );

  useEffect(() => {
    scrollToBottom();
  }, [showTopics, scrollToBottom]);

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

export default function Messages() {
  const { chatMessages, chatType, setChatType, isThinking, scrollToBottom } =
    useChatStore(
      useShallow((state) => ({
        chatMessages: state.chatMessages,
        chatType: state.chatType,
        showTopics: state.showTopics,
        setChatType: state.setChatType,
        isThinking: state.isThinking,
        scrollToBottom: state.scrollToBottom,
      }))
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
              return (
                <div
                  key={message.id}
                  className={`flex ${
                    message.type === ChatMessageTypeOptions.USER
                      ? "justify-end"
                      : "justify-start"
                  } animate-slideIn items-start`}
                >
                  {message.type === ChatMessageTypeOptions.AGENT && (
                    <div className="flex-shrink-0 hidden lg:block mr-2">
                      <div className="w-8 h-8 rounded-full bg-blue-200 flex items-center justify-center font-bold text-blue-700 border border-blue-300">
                        A
                      </div>
                    </div>
                  )}
                  <div
                    className={`text-left ${
                      isFloating ? "p-2" : "p-6"
                    } relative max-w-full rounded-lg rounded-tr-sm ${
                      message.type === ChatMessageTypeOptions.USER
                        ? isFloating
                          ? "bg-gradient-to-br from-purple-500 to-blue-500 md:max-w-[70%] shadow-lg text-white"
                          : "bg-gradient-to-br from-sky-500 to-blue-500 md:max-w-[50%] shadow-lg text-white"
                        : isFloating
                          ? "bg-white text-slate-800 rounded-2xl rounded-tl-sm w-full border border-purple-100"
                          : "bg-white text-slate-800 rounded-2xl rounded-tl-sm md:!max-w-[70%] border border-sky-100"
                    }`}
                  >
                    {index === chatMessages.length - 1 && <div id={SCROLL_TO_BOTTOM_ID} />}
                    <RenderReactMarkdown message={message} />
                    {message.references?.length &&
                    message.references.length > 0 ? (
                      <ul className="mt-2">
                        {message.references.map((reference) => (
                          <ReferenceDisplay
                            key={reference.url}
                            reference={reference}
                          />
                        ))}
                      </ul>
                    ) : null}
                  </div>

                  {message.type === ChatMessageTypeOptions.USER && (
                    <div className="flex-shrink-0 hidden lg:block ml-2">
                      <div className="w-8 h-8 rounded-full bg-purple-200 flex items-center justify-center font-bold text-purple-700 border border-purple-300">
                        U
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
            <ConversationTopics />
            <TopicSwitcher />
            {/* Thinking Indicator */}
            {isThinking && <ThinkingIndicator />}
          </div>
        </div>
      </div>
    </div>
  );
}
