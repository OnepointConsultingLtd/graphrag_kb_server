import { useShallow } from "zustand/react/shallow";
import useChatStore from "../context/chatStore";
import { ChatMessageTypeOptions } from "../model/message";
import RenderReactMarkdown from "./main-chat/RenderReactMarkdown";

export const MARKDOWN_DIALOGUE_ID = "markdown-dialogue";

export default function MarkdownDialogue() {
  const [setIsMarkdownDialogueOpen, markdownDialogueContent] = useChatStore(
    useShallow((state) => [
      state.setIsMarkdownDialogueOpen,
      state.markdownDialogueContent,
    ]),
  );

  const handleDialogueClose = () => {
    setIsMarkdownDialogueOpen(false);
  };

  return (
    <dialog
      id={MARKDOWN_DIALOGUE_ID}
      className="modal"
      onClick={handleDialogueClose}
    >
      <div
        className="modal-box w-[90%] max-w-4xl max-h-[80vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <form method="dialog">
          <button className="btn btn-sm btn-circle btn-ghost absolute right-2 top-2">
            ✕
          </button>
        </form>
        <RenderReactMarkdown
          message={{
            id: "1",
            text: markdownDialogueContent.replace(/<!--[\s\S]*?-->/g, ""),
            type: ChatMessageTypeOptions.AGENT,
            timestamp: new Date(),
          }}
          listItemClassName="text-gray-100"
        />
        <div className="modal-action">
          <button onClick={handleDialogueClose} className="btn btn-primary">
            <span className="font-medium">Close</span>
          </button>
        </div>
      </div>
    </dialog>
  );
}
