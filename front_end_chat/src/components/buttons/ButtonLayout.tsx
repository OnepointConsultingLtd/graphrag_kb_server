import { useShallow } from "zustand/react/shallow";
import useChatStore from "../../context/chatStore";
import { ChatType } from "../../lib/chatTypes";

export function ButtonLayout({ children }: { children: React.ReactNode }) {
  const { chatType } = useChatStore(
    useShallow((state) => ({
      chatType: state.chatType,
    })),
  );
  return (
    <div
      className={`grid overflow-x-hidden grid-cols-1 lg:grid-cols-${chatType === ChatType.FLOATING ? 2 : 4} md:grid-cols-2 w-full gap-3`}
    >
      {children}
    </div>
  );
}
