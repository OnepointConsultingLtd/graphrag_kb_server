import { useShallow } from "zustand/react/shallow";
import useChatStore from "../../context/chatStore";

function NewChatButton() {
    const clearChatMessages = useChatStore(useShallow((state) => state.clearChatMessages));
    return <div className="flex justify-start">
        <button
            onClick={clearChatMessages}
            className="btn btn-primary"
        >
            <svg
                className="w-5 h-5 transition-transform duration-500 ease-out group-hover:rotate-90"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
            >
                <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2.5"
                    d="M12 4v16m8-8H4"
                />
            </svg>
            <span className="font-medium md:!block !hidden">New Chat</span>
        </button>
    </div>
}

function LogoutButton() {
    const { logout } = useChatStore(useShallow((state) => ({
        logout: state.logout
    })));
    return <button
        onClick={logout}
        className="btn btn-secondary"
    >
        <svg stroke="currentColor" fill="currentColor" stroke-width="0" viewBox="0 0 512 512" height="25px" width="25px" xmlns="http://www.w3.org/2000/svg">
        <path d="M312 372c-7.7 0-14 6.3-14 14 0 9.9-8.1 18-18 18H94c-9.9 0-18-8.1-18-18V126c0-9.9 8.1-18 18-18h186c9.9 0 18 8.1 18 18 0 7.7 6.3 14 14 14s14-6.3 14-14c0-25.4-20.6-46-46-46H94c-25.4 0-46 20.6-46 46v260c0 25.4 20.6 46 46 46h186c25.4 0 46-20.6 46-46 0-7.7-6.3-14-14-14z"></path><path d="M372.9 158.1c-2.6-2.6-6.1-4.1-9.9-4.1-3.7 0-7.3 1.4-9.9 4.1-5.5 5.5-5.5 14.3 0 19.8l65.2 64.2H162c-7.7 0-14 6.3-14 14s6.3 14 14 14h256.6L355 334.2c-5.4 5.4-5.4 14.3 0 19.8l.1.1c2.7 2.5 6.2 3.9 9.8 3.9 3.8 0 7.3-1.4 9.9-4.1l82.6-82.4c4.3-4.3 6.5-9.3 6.5-14.7 0-5.3-2.3-10.3-6.5-14.5l-84.5-84.2z"></path></svg>
        <span className="font-medium md:!block !hidden">Logout</span>
    </button>
}

function ProjectName() {
    const { selectedProject } = useChatStore(useShallow((state) => ({
        selectedProject: state.selectedProject
    })));
    return <div className="flex items-center space-x-4 pr-4">
        <div className="w-10 h-10 md:w-12 md:h-12 bg-[#0ea5e9] rounded-full flex items-center justify-center">
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
                Simple Chat Interface
            </p>
        </div>
    </div>
}

export default function Header() {
    return (
        <div className="w-full mx-auto">
            <div className="flex justify-between items-center">
                <header className="p-3 w-full relative !-50">
                    <div className="flex items-center space-x-4 w-full justify-between">
                        <ProjectName />
                        <div className="flex items-center space-x-4">
                            <NewChatButton />
                            <LogoutButton />
                        </div>
                    </div>
                </header>
            </div>
        </div>
    );
}