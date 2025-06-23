import { useShallow } from "zustand/react/shallow";
import useChatStore from "../../context/chatStore";
import { IoMdLogOut } from "react-icons/io";
import { MdAutorenew } from "react-icons/md";
import { MdNewLabel } from "react-icons/md";
import ButtonWrapper from "../Buttons/ButtonWrapper";

export function NewChatButton() {
  const clearChatMessages = useChatStore(
    useShallow((state) => state.clearChatMessages)
  );

  return (
    <ButtonWrapper onClick={clearChatMessages} name="New Chat">
      <MdAutorenew className="text-2xl" />
    </ButtonWrapper>
  );
}

export function NewProject() {
  const { newProject } = useChatStore(
    useShallow((state) => ({
      newProject: state.newProject,
    }))
  );

  const handleNewProject = () => {
    newProject();
  };

  return (
    <ButtonWrapper onClick={handleNewProject} name="Switch Project">
      <MdNewLabel className="text-2xl" />
    </ButtonWrapper>
  );
}

function LogoutButton() {
  const { logout } = useChatStore(
    useShallow((state) => ({
      logout: state.logout,
    }))
  );

  return (
    <ButtonWrapper onClick={logout} name="Logout">
      <IoMdLogOut className="text-2xl" />
    </ButtonWrapper>
  );
}

function ProjectName() {
  const { selectedProject } = useChatStore(
    useShallow((state) => ({
      selectedProject: state.selectedProject,
    }))
  );
  return (
    <div className="flex items-center space-x-4 pr-4">
      <div className="w-10 h-10 md:w-12 md:h-12 bg-[#0ea5e9] rounded-full hidden md:flex items-center justify-center">
        <svg
          className="w-6 h-6 text-white"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
          />
        </svg>
      </div>
      <div className="text-left">
        <h1 className="text-xl md:text-3xl font-bold text-[#0284c7]">
          {selectedProject?.name?.replace("_", " ")}
        </h1>
        <p className="text-[#64748b] lg:text-base text-sm">
          {selectedProject?.platform} - {selectedProject?.search_type}
        </p>
      </div>
    </div>
  );
}

export default function Header() {
  const { chatMessages } = useChatStore(
    useShallow((state) => ({
      chatMessages: state.chatMessages,
    }))
  );

  return (
    <div className="w-full mx-auto">
      <div className="flex justify-between items-center">
        <header className="p-3 w-full relative !-50">
          <div className="flex items-center space-x-4 w-full justify-between">
            <ProjectName />
            <div className="flex items-center space-x-4">
              {!!chatMessages.length && chatMessages.length > 0 && (
                <NewChatButton />
              )}
              <NewProject />
              <LogoutButton />
            </div>
          </div>
        </header>
      </div>
    </div>
  );
}
