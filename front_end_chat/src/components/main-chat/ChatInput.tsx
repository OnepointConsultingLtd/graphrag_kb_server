import { useEffect, useMemo } from "react";
import { useShallow } from "zustand/react/shallow";
import useChatStore from "../../context/chatStore";
import Send from "../icons/Send";
import { ChatType } from "../../lib/chatTypes";

export default function ChatInput() {
  const [
    inputText,
    isThinking,
    sendUserMessage,
    setInputText,
    chatType
  ] = useChatStore(
    useShallow((state) => [
      state.inputText,
      state.isThinking,
      state.sendUserMessage,
      state.setInputText,
      state.chatType,
    ]),
  );

  const isFloating = chatType === ChatType.FLOATING;

  function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    sendUserMessage();
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
      <div className="mx-auto w-full pt-1">
        <div className="flex flex-col gap-2 mx-0">
          <form onSubmit={onSubmit} className="relative">
            <textarea
              id="chat-input"
              value={inputText}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
                setInputText(e.target.value)
              }
              placeholder="Type your message here..."
              className={`w-full ${isFloating ? "bg-white text-gray-900" : "bg-gray-900 text-white"} p-4 pr-14 lg:pr-4 overflow-hidden transition-all duration-300 border-2 
                                shadow-sm outline-none resize-none rounded-xl border-sky-100 
                                focus:border-sky-400 focus:ring-4 focus:ring-sky-100 disabled:opacity-50 disabled:cursor-not-allowed`}
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
              className="btn absolute right-3 bottom-4 bg-white px-2 hover:bg-gray-200 text-blue-500 p-2 rounded-lg cursor-pointer flex items-center gap-2"
              aria-label={
                isThinking ? "Processing your message" : "Send message"
              }
            >
              <Send />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
