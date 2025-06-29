import ReactMarkdown from "react-markdown";
import { useShallow } from "zustand/react/shallow";
import useChatStore from "../../context/chatStore";
import type { ChatMessage } from "../../model/message";
import { ChatMessageType } from "../../model/message";
import MessageTimestamp from "../messages/MessageTimestamp";
import CopyButton from "./CopyButton";

async function copyToClipboard(text: string) {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
    } else {
      // Fallback for browsers that don't support clipboard API
      const textArea = document.createElement("textarea");
      textArea.value = text;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand("copy");
      document.body.removeChild(textArea);
    }
  } catch (error) {
    console.error("Failed to copy text: ", error);
  }
}

export default function RenderReactMarkdown({
  message,
  listItemClassName = "text-slate-600",
}: {
  message: ChatMessage;
  listItemClassName?: string;
}) {
  const setCopiedMessageId = useChatStore(
    useShallow((state) => state.setCopiedMessageId),
  );

  return (
    <>
      <ReactMarkdown
        components={{
          a: ({ ...props }) => (
            <a
              {...props}
              className={`underline ${
                message.type === ChatMessageType.USER
                  ? "text-purple-100 hover:text-white"
                  : "text-purple-500 hover:text-purple-600"
              } transition-colors duration-200`}
              target="_blank"
              rel="noopener noreferrer"
            />
          ),
          p: ({ ...props }) => (
            <p
              {...props}
              className={message.type === ChatMessageType.USER ? "" : `mb-4`}
            />
          ),
          ul: ({ ...props }) => (
            <ul {...props} className="my-4 ml-4 space-y-2 list-disc" />
          ),
          li: ({ ...props }) => (
            <li
              {...props}
              className={`break-all ${
                message.type === ChatMessageType.USER
                  ? "text-white"
                  : listItemClassName
              }`}
            />
          ),
        }}
      >
        {message.text}
      </ReactMarkdown>

      {/* Date and copy button */}
      <div className="flex items-center justify-between mt-2 text-xs">
        <div
          className={
            message.type === ChatMessageType.USER
              ? "text-purple-100"
              : "text-slate-400"
          }
        >
          <MessageTimestamp
            timestamp={
              typeof message.timestamp === "string"
                ? message.timestamp
                : message.timestamp.toISOString()
            }
          />
        </div>

        <CopyButton
          isUser={message.type === ChatMessageType.USER}
          text={message.text}
          id={message.id}
          onCopy={() => {
            copyToClipboard(message.text);
            setCopiedMessageId(message.id);
            setTimeout(() => setCopiedMessageId(""), 1500);
          }}
        />
      </div>
    </>
  );
}
