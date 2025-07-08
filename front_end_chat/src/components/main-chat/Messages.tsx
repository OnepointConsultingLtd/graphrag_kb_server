import { useEffect } from "react";
import { useShallow } from "zustand/react/shallow";
import useChatStore from "../../context/chatStore";
import { ChatMessageTypeOptions } from "../../model/message";
import ReferenceDisplay from "../messages/ReferenceDisplay";
import RenderReactMarkdown from "./RenderReactMarkdown";
import ThinkingIndicator from "./ThinkingIndicator";
import { ChatType } from "../../lib/chatTypes";
import { ChatTypeOptions } from "../../model/types";
import { fetchTopics } from "../../lib/apiClient";
import useWebsocket from "../../hooks/useWebsocket";
import { Topic } from "../../model/topics";
import { SCROLL_TO_BOTTOM_ID } from "../../constants/scroll";

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
      <svg
        stroke="currentColor"
        fill="currentColor"
        strokeWidth="0"
        viewBox="0 0 512 512"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path d="M119.436 36c-16.126 0-29.2 17.237-29.2 38.5v363c0 21.263 13.074 38.5 29.2 38.5h275.298c16.126 0 29.198-17.237 29.198-38.5v-363c0-21.263-13.072-38.5-29.198-38.5zm26.369 10.951l11.002 32.856 34.648.312-27.848 20.617 10.41 33.05-28.212-20.114-28.215 20.113L128 100.736 100.152 80.12l34.649-.312zM363.979 161.84c7.127 9.459 12.739 20.689 16.832 32.04 3.8 10.544 6.197 21.211 6.668 31.02-.163 19.015-3.915 23.274-14.557 36.934l-6.703-11.48c-10.85-13.106-30.779-48.4-47.383-43.672-6.521 6.11-8.996 13.37-10.313 20.802 2.898 8.8 4.477 18.43 4.477 28.516 0 15.293-3.615 29.54-9.996 41.416 22.643 4.537 57.927 19.332 57.973 39.223-.27 3.783-1.835 7.68-4.362 10.42-10.743 12.528-36.958 4.125-45.2 10.072.796 6.947 4.112 14.118 4.355 20.174.136 4.36-1.768 10.58-6.508 13.996-5.67 4.087-12.968 4.551-18.52 3.045C279.94 392.226 272 379.649 256 377c-13.544 3.491-22.412 13.87-34.742 17.346-5.552 1.506-12.85 1.042-18.52-3.045-4.74-3.417-6.644-9.636-6.508-13.996-.058-7.142 4.107-13.794 4.356-20.174-15.741-7.788-33.816 1.97-45.201-10.072-2.527-2.74-4.093-6.637-4.362-10.42 6.146-27.341 35.374-34.684 57.973-39.223C202.615 285.54 199 271.293 199 256c0-11.489 2.047-22.385 5.764-32.135-2.357-7.923-3.441-15.988-9.438-22.441-8.758-.925-14.079 6.897-17.842 12.63-11.683 19.5-18.718 30.606-32.88 46.192-16.604-23.4-19.314-49.29-13.157-70.988 6.065-20.331 19.17-38.798 37.926-47.924 21.216-9.766 39.872-10.03 58.885.203 5.163-13.053 10.4-25.65 18.035-36.209 9.625-13.31 23.8-25.631 43.707-25.295 38.8.656 73.993 51.156 73.979 81.807zm-72.22-63.893c-35.759 2.409-44.771 44.746-55.189 71.29l-9.447-7.087c-18.428-12.31-31.076-13.732-49.875-4.63-12.924 6.288-23.701 20.62-28.553 36.882-3.38 11.329-3.765 23.225-.949 33.645 9.45-13.549 15.806-30.08 28.317-39.178 7.486-7.975 26.27-8.498 35.45 3.897 4.838 7.02 7.437 14.54 9.5 22.234h72.165c.592-1.944 1.067-3.762 2.017-6.033 2.956-7.064 7.765-16.266 18.395-19.504 18.09-3.862 32.494 7.106 43.498 18.514 4.517 4.717 8.492 9.696 12.098 14.517-.69-6.798-2.477-14.651-5.31-22.508-13.127-36.707-37.889-51.031-70.386-32.011 2.556-16.423 16.87-35.72 46.25-26.962-9.094-17.135-30.355-42.471-47.98-43.066zM220.644 233c-2.31 6.965-3.643 14.753-3.643 23 0 15.85 4.892 30.032 12.26 39.855C236.628 305.68 245.988 311 256 311c10.012 0 19.372-5.32 26.74-15.145C290.108 286.032 295 271.85 295 256c0-8.247-1.334-16.035-3.643-23zM232 280h48s-8 14-24 14-24-14-24-14zm-11.14 33.566c-13.86 3.34-50.369 8.9-51.842 21.42 9.621 1.947 20.446.838 28.998 2.235 5.993 1.018 12.82 3.323 17.285 9.517 3.375 4.683 3.577 10.103 3.037 14.21-.543 5.89-3.317 10.557-3.975 16.32 15.955-2.59 28.264-17.532 41.637-18.268 16-.702 29.313 17.402 41.637 18.268-.893-5.59-3.262-11.158-3.975-16.32-.54-4.107-.338-9.527 3.037-14.21 4.465-6.194 11.292-8.5 17.285-9.517 9.742-2.229 19.975.396 28.998-2.235-5.77-13.125-39.813-19.454-51.841-21.42C281.665 323.01 269.45 329 256 329c-13.452 0-25.665-5.991-35.14-15.434zm117.122 64.649l28.213 20.113 28.215-20.113L384 411.264l27.848 20.617-34.649.312-11.004 32.856-11.002-32.856-34.648-.312 27.848-20.617z"></path>
      </svg>
    </button>
  );
}

const INCREMENT_TOPICS_NUMBER = 4;

const INCREMENT_TOPICS_BUTTON_ID = "increment-topics-button";

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
            </div>
            <JokerButton />
          </div>
        )}
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
      }))
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

export default function Messages() {
  const { chatMessages, chatType, setChatType, isThinking, scrollToBottom } =
    useChatStore(
      useShallow((state) => ({
        chatMessages: state.chatMessages,
        chatType: state.chatType,
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
                  {index === chatMessages.length - 1 && (
                    <div id={SCROLL_TO_BOTTOM_ID} />
                  )}
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
