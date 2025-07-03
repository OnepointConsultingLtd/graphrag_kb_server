import { useEffect, useMemo } from "react";
import { v4 as uuidv4 } from "uuid";
import { useShallow } from "zustand/react/shallow";
import useChatStore from "../../context/chatStore";
import { sendQuery } from "../../lib/apiClient";
import { extractSimpleReferences } from "../../lib/referenceExtraction";
import { ChatMessageType, type QueryResponse } from "../../model/message";

export default function ChatInput() {
  const [
    inputText,
    jwt,
    isThinking,
    selectedProject,
    chatMessages,
    addChatMessage,
    setIsThinking,
    setInputText,
    conversationId,
  ] = useChatStore(
    useShallow((state) => [
      state.inputText,
      state.jwt,
      state.isThinking,
      state.selectedProject,
      state.chatMessages,
      state.addChatMessage,
      state.setIsThinking,
      state.setInputText,
      state.conversationId,
    ]),
  );

  function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setIsThinking(true);
    setInputText("");
    addChatMessage({
      id: uuidv4(),
      text: inputText,
      type: ChatMessageType.USER,
      timestamp: new Date(),
    });
    if (selectedProject) {
      sendQuery({
        jwt,
        question: inputText,
        project: selectedProject,
        chatHistory: chatMessages,
        conversationId: conversationId ?? crypto.randomUUID(),
      })
        .then((response: QueryResponse) => {
          console.info("response", response);
          const finalResponse =
            response?.response?.response ?? response?.response;
          const references = extractSimpleReferences(response?.response);
          addChatMessage({
            id: uuidv4(),
            text: finalResponse,
            type: ChatMessageType.AGENT,
            timestamp: new Date(),
            references: references,
          });
        })
        .catch((error) => {
          console.error("error", error);
          addChatMessage({
            id: uuidv4(),
            text: `An error occurred while processing your request: ${error.message}. Please try again.`,
            type: ChatMessageType.AGENT_ERROR,
            timestamp: new Date(),
          });
        })
        .finally(() => {
          setIsThinking(false);
        });
    }
  }

  useEffect(() => {
    if (!isThinking) {
      document.getElementById("chat-input")?.focus();
    }
  }, [isThinking]);

  const textareaStyle = useMemo(() => {
    const baseHeight = 24;
    return {
      height:
        Math.min(
          baseHeight * 2 - 10 + baseHeight * inputText.split("\n").length,
          200,
        ) + "px",
    };
  }, [inputText]);

  return (
    <div className="sticky bottom-0">
      <div className="mx-auto w-full py-2 lg:py-4">
        <div className="flex flex-col gap-2 mx-4">
          <form onSubmit={onSubmit} className="relative">
            <textarea
              id="chat-input"
              value={inputText}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
                setInputText(e.target.value)
              }
              placeholder="Type your message here..."
              className="w-full bg-gray-900 p-4 pr-24 overflow-hidden transition-all duration-300 border-2 
                                shadow-sm outline-none resize-none rounded-xl border-sky-100 
                                focus:border-sky-400 focus:ring-4 focus:ring-sky-100 disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={isThinking}
              style={textareaStyle}
              onKeyDown={(e: React.KeyboardEvent<HTMLTextAreaElement>) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  const form = e.currentTarget.form;
                  if (form) form.requestSubmit();
                }
              }}
            />

            <button
              type="submit"
              disabled={isThinking || inputText.trim() === ""}
              className="absolute lg:hidden right-4 bottom-4 bg-white px-4 hover:bg-gray-200 text-blue-500 p-2 rounded-lg cursor-pointer flex items-center gap-2"
              aria-label={
                isThinking ? "Processing your message" : "Send message"
              }
            >
              Send
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
