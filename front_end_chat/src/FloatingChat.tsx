import { useState } from "react";
import { useShallow } from "zustand/shallow";
import FloatingChatButton from "./components/floating-chat/FloatingChatButton";
import FloatingChatMain from "./components/floating-chat/FloatingChatMain";
import FloatingIntro from "./components/floating-chat/FloatingIntro";
import MarkdownDialogue from "./components/MarkdownDialogue";
import useChatStore from "./context/chatStore";

const FloatingChat = () => {
  const [isFloatingOpen, setIsFloatingOpen] = useState(false);
  const { displayFloatingChatIntro } = useChatStore(
    useShallow((state) => ({
      displayFloatingChatIntro: state.displayFloatingChatIntro,
    })),
  );

  const handleFloatingBtn = () => {
    setIsFloatingOpen(!isFloatingOpen);
  };

  return (
    <div className="!w-full max-w-full bg-gradient-to-br ">
      <div className="relative z-10 w-full !max-w-full">
        {/* Hero Section */}
        {displayFloatingChatIntro && (
          <FloatingIntro handleFloatingBtn={handleFloatingBtn} />
        )}

        {/* Floating Chat */}
        {isFloatingOpen ? (
          <div className="sm:fixed bottom-10 right-8 z-50">
            <MarkdownDialogue />
            <FloatingChatMain handleFloatingBtn={handleFloatingBtn} />
          </div>
        ) : (
          <FloatingChatButton click={handleFloatingBtn} />
        )}
      </div>
    </div>
  );
};

export default FloatingChat;
