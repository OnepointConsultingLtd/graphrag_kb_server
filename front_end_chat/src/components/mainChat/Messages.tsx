import useChatStore from "../../context/chatStore";
import { useShallow } from "zustand/react/shallow";
import { ChatMessageType } from "../../model/message";
import RenderReactMarkdown from "./RenderReactMarkdown";


export default function Messages() {
    const { chatMessages, isFloating } = useChatStore(useShallow((state) => ({
        chatMessages: state.chatMessages,
        isFloating: state.isFloating
    })));
    return (
        <div className="flex-1 flex-col mb-[4rem]">
            <div className="overflow-y-auto">
                <div className="mx-auto">
                    <div className="flex flex-col gap-6 p-4">
                        {chatMessages.map((message) => (
                            <div
                                key={message.id}
                                className={`flex ${message.type === ChatMessageType.USER ? "justify-end" : "justify-start"} animate-slideIn`}
                            >
                                <div
                                    className={`text-left ${isFloating ? "p-2" : "p-6"} relative ${message.type === ChatMessageType.USER
                                            ? isFloating
                                                ? "bg-gradient-to-br from-purple-500 to-blue-500 text-white rounded-lg rounded-tr-sm max-w-[85%] md:max-w-[70%] shadow-lg"
                                                : "bg-gradient-to-br from-sky-500 to-blue-500 text-white rounded-lg rounded-tr-sm max-w-[85%] md:max-w-[50%] shadow-lg"
                                            : isFloating
                                                ? "bg-white text-slate-800 rounded-2xl rounded-tl-sm w-full border border-purple-100"
                                                : "bg-white text-slate-800 rounded-2xl rounded-tl-sm !max-w-[85%] md:!max-w-[70%] border border-sky-100"
                                        }`}
                                >
                                    <RenderReactMarkdown message={message} />
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    )
}