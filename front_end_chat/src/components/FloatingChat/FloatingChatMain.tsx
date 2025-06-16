import { useEffect } from "react";
import { IoIosArrowDown } from "react-icons/io";
import { useShallow } from "zustand/shallow";
import useChatStore from "../../context/chatStore";
import ChatInput from "../mainChat/ChatInput";
import { NewChatButton } from "../mainChat/Header";
import Messages from "../mainChat/Messages";

export default function FloatingChatMain({
  handleFloatingBtn,
}: {
  handleFloatingBtn: () => void;
}) {
  const { selectedProject, setIsFloating } = useChatStore(
    useShallow((state) => ({
      selectedProject: state.selectedProject,
      setIsFloating: state.setIsFloating,
    }))
  );

  useEffect(() => {
    setIsFloating(true);
  }, [setIsFloating]);

  return (
    <div className="sm:!h-[calc(100vh-130px)] !h-[calc(100dvh)]  !w-full lg:!w-[436px] bg-white rounded-2xl shadow-2xl border border-gray-200 overflow-hidden animate-in slide-in-from-bottom-4 duration-300 flex flex-col justify-between relative">
      <div className="flex flex-col flex-1 ">
        {/* Header */}
        <header className="sticky justify-between top-0 z-10 w-full rounded-xl px-4 py-4 bg-gradient-to-r from-[#e0f2fe] via-[#38bdf8] to-[#0284c7] flex items-center">
          <div className="flex flex-col">
            <span className="text-2xl font-bold mr-3 select-none">
              <span className="text-[#0284c7]">One</span>
              <span className="text-[#2563eb]">point</span>
            </span>
            <h1 className="!text-sm md:!text-base font-bold text-white">
              {selectedProject?.name || "Unknown Project"}
            </h1>
          </div>

          <div className="flex items-center justify-between space-x-4">
            {/* Restart Button */}
            <NewChatButton />
          </div>

          {/* Close chat */}
          <button
            className="flex justify-center py-3 cursor-pointer group absolute top-4 mx-auto right-4 left-4 w-fit"
            onClick={handleFloatingBtn}
          >
            <IoIosArrowDown className="text-4xl font-bold" />
          </button>
        </header>

        {/* Messages Container */}
        <div className="flex-1 h-screen overflow-y-auto">
          <Messages />
        </div>
        <div className="mt-2 px-4 pb-4">
          <ChatInput />
        </div>
      </div>
    </div>
  );
}
