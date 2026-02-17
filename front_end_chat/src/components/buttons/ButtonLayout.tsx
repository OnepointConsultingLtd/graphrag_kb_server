import { ChatType } from "../../lib/chatTypes";
import useChatStore from "../../context/chatStore";
import { useShallow } from "zustand/shallow";

export function ButtonLayout({ children }: { children: React.ReactNode }) {
  const { chatType } = useChatStore(
    useShallow((state) => ({
      chatType: state.chatType,
    })),
  );
  const isFloating = chatType === ChatType.FLOATING;
  return (
    <div
      className={`grid overflow-x-hidden grid-cols-1 ${isFloating ? "" : "md:grid-cols-2"} w-full gap-3`}
    >
      {children}
    </div>
  );
}
