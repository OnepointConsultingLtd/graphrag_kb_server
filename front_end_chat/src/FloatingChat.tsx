import { useState } from "react";
import { useShallow } from "zustand/shallow";
import FloatingChatButton from "./components/FloatingChat/FloatingChatButton";
import FloatingChatMain from "./components/FloatingChat/FloatingChatMain";
import FloatingIntro from "./components/FloatingChat/FloatingIntro";
import MarkdownDialogue from "./components/MarkdownDialogue";
import useChatStore from "./context/chatStore";

const FloatingChat = () => {
  const [isFloatingOpen, setIsFloatingOpen] = useState(false);
  const { displayFloatingChatIntro } = useChatStore(
    useShallow((state) => ({
      displayFloatingChatIntro: state.displayFloatingChatIntro,
    }))
  );

  const handleFloatingBtn = () => {
    setIsFloatingOpen(!isFloatingOpen);
  };

  return (
    <div className="min-h-screen !w-full max-w-full bg-gradient-to-br ">
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-purple-300 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-yellow-300 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob animation-delay-2000"></div>
        <div className="absolute top-40 left-40 w-80 h-80 bg-pink-300 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob animation-delay-4000"></div>
      </div>

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
