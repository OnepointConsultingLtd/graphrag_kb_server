import { FaCheckSquare, FaRegCopy } from "react-icons/fa";
import { useShallow } from "zustand/react/shallow";
import useChatStore from "../../context/chatStore";

export default function CopyButton({
  text,
  id,
  onCopy,
  isUser,
}: {
  id: string;
  text: string;
  onCopy: (text: string, id: string) => void;
  isUser: boolean;
}) {
  const { copiedMessageId } = useChatStore(
    useShallow((state) => ({
      copiedMessageId: state.copiedMessageId,
    })),
  );
  const isActive = copiedMessageId === id;

  const baseColorClass = "text-[#64748b] hover:text-[#0ea5e9]";

  return (
    <button
      onClick={() => onCopy(text, id)}
      className={`
          p-1 rounded-md
          ${baseColorClass}
          before:opacity-90 before:rounded-lg
          hover:before:opacity-100
          active:scale-95
          transition-all duration-200
          cursor-pointer
          relative
        `}
      title={isActive ? "Copied!" : "Copy to clipboard"}
    >
      <span className="relative block w-4 h-4 transition-all duration-300 hover:scale-110">
        {isActive ? (
          <FaCheckSquare
            className={`${isUser ? "text-green-500" : "text-blue-500"}`}
          />
        ) : (
          <FaRegCopy className={`${isUser ? "text-white" : "text-blue-500"}`} />
        )}
      </span>
    </button>
  );
}
