import { useEffect } from "react";
import { useShallow } from "zustand/react/shallow";
import useChatStore from "../../context/chatStore";
import { ChatMessageType } from "../../model/message";
import ReferenceDisplay from "../Messages/ReferenceDisplay";
import RenderReactMarkdown from "./RenderReactMarkdown";
import ThinkingIndicator from "./ThinkingIndicator";

export default function Messages() {
  const { chatMessages, isFloating, setIsFloating, isThinking } = useChatStore(
    useShallow((state) => ({
      chatMessages: state.chatMessages,
      isFloating: state.isFloating,
      setIsFloating: state.setIsFloating,
      isThinking: state.isThinking,
    }))
  );

  useEffect(() => {
    setIsFloating(false);
  }, [setIsFloating]);

  return (
    <div className="flex-1 flex-col mb-[4rem]">
      <div className="overflow-y-auto">
        <div className="mx-auto">
          <div className={`flex flex-col gap-6 ${isFloating ? "p-1" : "p-6"}`}>
            {chatMessages.map((message) => (
              <div
                key={message.id}
                className={`flex ${
                  message.type === ChatMessageType.USER
                    ? "justify-end"
                    : "justify-start"
                } animate-slideIn items-end`}
              >
                {message.type === ChatMessageType.AGENT && (
                  <div className="flex-shrink-0 mr-2">
                    <div className="w-8 h-8 rounded-full bg-blue-200 flex items-center justify-center font-bold text-blue-700 border border-blue-300">
                      A
                    </div>
                  </div>
                )}
                <div
                  className={`text-left ${
                    isFloating ? "p-2" : "p-6"
                  } relative ${
                    message.type === ChatMessageType.USER
                      ? isFloating
                        ? "bg-gradient-to-br from-purple-500 to-blue-500 text-white rounded-lg rounded-tr-sm max-w-[85%] md:max-w-[70%] shadow-lg"
                        : "bg-gradient-to-br from-sky-500 to-blue-500 text-white rounded-lg rounded-tr-sm max-w-[85%] md:max-w-[50%] shadow-lg"
                      : isFloating
                      ? "bg-white text-slate-800 rounded-2xl rounded-tl-sm w-full border border-purple-100"
                      : "bg-white text-slate-800 rounded-2xl rounded-tl-sm !max-w-[85%] md:!max-w-[70%] border border-sky-100"
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
                  <div className="flex-shrink-0 ml-2">
                    <div className="w-8 h-8 rounded-full bg-purple-200 flex items-center justify-center font-bold text-purple-700 border border-purple-300">
                      U
                    </div>
                  </div>
                )}
              </div>
            ))}
            {isThinking && <ThinkingIndicator />}
          </div>
        </div>
      </div>
    </div>
  );
}
