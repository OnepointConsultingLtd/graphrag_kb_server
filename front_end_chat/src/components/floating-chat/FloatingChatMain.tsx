import { useEffect } from "react";
import { IoIosArrowDown } from "react-icons/io";
import { useShallow } from "zustand/shallow";
import useChatStore from "../../context/chatStore";
import ChatInput from "../main-chat/ChatInput";
import { NewChatButton } from "../main-chat/Header";
import { ChatType } from "../../lib/chatTypes";
import { ChatTypeOptions } from "../../model/types";
import Messages from "../main-chat/Messages";

export default function FloatingChatMain({
  handleFloatingBtn,
}: {
  handleFloatingBtn: () => void;
}) {
  const { selectedProject, setChatType, organisation_name } = useChatStore(
    useShallow((state) => ({
      selectedProject: state.selectedProject,
      setChatType: state.setChatType,
      organisation_name: state.organisation_name,
    })),
  );

  useEffect(() => {
    setChatType(ChatType.FLOATING as ChatTypeOptions);
  }, [setChatType]);

  return (
    <div
      className="sm:!h-[calc(100vh-130px)] !h-[calc(100dvh)]  !w-full sm:!w-[436px] bg-white sm:rounded-2xl shadow-2xl border border-gray-200 overflow-hidden animate-in slide-in-from-bottom-4 duration-300 flex flex-col justify-between relative"
      id="floating-chat-main-container"
    >
      <div className="flex flex-col flex-1 min-h-0 ">
        {/* Header */}
        <header className="sticky justify-between top-0 z-10 w-full sm:rounded-xl px-4 py-4 bg-gradient-to-r from-[#2ba7fb] via-[#38bdf8] to-[#0284c7] !flex items-center">
          <div className="flex flex-col">
            <span className="text-2xl font-bold mr-3 select-none">
              <span className="text-white" id="organisation-name">
                {organisation_name}{" "}
              </span>
            </span>
            <h1
              className="!text-sm md:!text-base font-bold text-white"
              id="project-name"
            >
              {selectedProject?.name.replace(/_/g, " ") || "Unknown Project"}
            </h1>
          </div>

          <div className="flex items-center justify-between space-x-4">
            {/* Restart Button */}
            <NewChatButton />
          </div>

          {/* Close chat */}
          <button
            className="flex justify-center py-3 cursor-pointer group absolute top-8 lg:top-4 mx-auto right-4 left-4 w-fit"
            onClick={handleFloatingBtn}
          >
            <IoIosArrowDown className="text-4xl font-bold" />
          </button>
        </header>

        {/* Messages Container */}
        <div className="chat-box flex-1 overflow-y-auto min-h-0">
          <Messages />
        </div>
        <div className="mt-1 px-1 pb-0">
          <ChatInput />
        </div>
      </div>
    </div>
  );
}
