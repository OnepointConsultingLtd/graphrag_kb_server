import { useEffect, useRef } from "react";
import { useShallow } from "zustand/react/shallow";
import useChatStore from "../../context/chatStore";
import { ChatMessageType } from "../../model/message";
import ReferenceDisplay from "../messages/ReferenceDisplay";
import RenderReactMarkdown from "./RenderReactMarkdown";
import ThinkingIndicator from "./ThinkingIndicator";
import { ChatType } from "../../lib/chatTypes";
import { ChatTypeOptions } from "../../types/types";
import { fetchTopics } from "../../lib/apiClient";

function ConversationStarter() {
  const {
    jwt,
    selectedProject,
    topics,
    setTopics,
    chatType,
    setInputText
  } = useChatStore(
    useShallow((state) => ({
      jwt: state.jwt,
      selectedProject: state.selectedProject,
      topics: state.topics,
      chatType: state.chatType,
      setTopics: state.setTopics,
      setInputText: state.setInputText,
    })),
  )

  useEffect(() => {
    if (jwt && selectedProject) {
      fetchTopics(jwt, selectedProject).then(setTopics).catch(console.error);
    }
  }, [jwt, selectedProject, setTopics]);

  if (!selectedProject) {
    return null;
  }

  const hasTopics = topics && topics.topics.length > 0;

  return (
    <div className="flex-1 flex items-center justify-center text-gray-500 mt-6">
      <div className="text-center">
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
        {hasTopics && <p className="mb-6">Select a topic to start a conversation...</p>}
        {hasTopics && <div 
          className={`grid lg:grid-cols-${chatType === ChatType.FLOATING ? 2 : 4} md:grid-cols-${chatType === ChatType.FLOATING ? 1 : 3} grid-cols-${chatType === ChatType.FLOATING ? 1 : 2} gap-2`}>
          {topics?.topics.map((topic) => (
            <button className="btn btn-primary h-18" key={`topic-${topic.name}-${topic.type}`} onClick={() => setInputText(`Tell me more about "${topic.name}"`)}>{topic.name}</button>
          ))}
        </div>}
      </div>
    </div >
  )
}

export default function Messages() {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const {
    chatMessages,
    chatType,
    setChatType,
    isThinking,
    scrollToBottom,

    setMessagesEndRef,
  } = useChatStore(
    useShallow((state) => ({
      chatMessages: state.chatMessages,
      chatType: state.chatType,
      setChatType: state.setChatType,
      isThinking: state.isThinking,
      scrollToBottom: state.scrollToBottom,
      setMessagesEndRef: state.setMessagesEndRef,
    })),
  );

  useEffect(() => {
    setChatType(ChatType.FULL_PAGE as ChatTypeOptions);
  }, [setChatType]);

  useEffect(() => {
    setMessagesEndRef(messagesEndRef.current);
  }, [setMessagesEndRef]);

  useEffect(() => {
    if (isThinking) {
      scrollToBottom();
    }
  }, [chatMessages, isThinking, scrollToBottom]);

  const isFloating = chatType === ChatType.FLOATING;

  return (
    <div className="flex-1 flex-col mb-[4rem]">
      <div className="overflow-y-auto">
        <div className="mx-auto">
          <div
            className={`flex flex-col gap-6 ${isFloating ? "p-1 pt-8" : "p-2 lg:p-6"
              }`}
          >
            {!chatMessages ||
              (chatMessages.length === 0 && <ConversationStarter />)}
            {chatMessages.map((message) => {
              console.log("message", message);
              return (
                <div
                  key={message.id}
                  className={`flex ${message.type === ChatMessageType.USER
                    ? "justify-end"
                    : "justify-start"
                    } animate-slideIn items-start`}
                >
                  {message.type === ChatMessageType.AGENT && (
                    <div className="flex-shrink-0 hidden lg:block mr-2">
                      <div className="w-8 h-8 rounded-full bg-blue-200 flex items-center justify-center font-bold text-blue-700 border border-blue-300">
                        A
                      </div>
                    </div>
                  )}
                  <div
                    className={`text-left ${isFloating ? "p-2" : "p-6"
                      } relative max-w-full rounded-lg rounded-tr-sm ${message.type === ChatMessageType.USER
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

                  {message.type === ChatMessageType.USER && (
                    <div className="flex-shrink-0 hidden lg:block ml-2">
                      <div className="w-8 h-8 rounded-full bg-purple-200 flex items-center justify-center font-bold text-purple-700 border border-purple-300">
                        U
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
            <div ref={messagesEndRef} />

            {/* Thinking Indicator */}
            {isThinking && <ThinkingIndicator />}
          </div>
        </div>
      </div>
    </div>
  );
}
