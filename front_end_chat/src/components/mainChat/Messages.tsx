import useChatStore from "../../context/chatStore";
import { useShallow } from "zustand/react/shallow";
import { ChatMessageType } from "../../model/message";
import RenderReactMarkdown from "./RenderReactMarkdown";
import ThinkingIndicator from "./ThinkingIndicator";
import type { Reference } from "../../model/references";
import { downloadFile } from "../../lib/apiClient";

function ReferenceDisplay({ reference }: { reference: Reference }) {
    const [jwt, project, setMarkdownDialogueContent] = useChatStore(useShallow((state) => 
        [state.jwt, state.selectedProject, state.setMarkdownDialogueContent]));

    function openReference(e: React.MouseEvent<HTMLAnchorElement>) {
        e.preventDefault();
        if (project) {
            downloadFile(jwt, project, reference)
            .then((content) => {
                setMarkdownDialogueContent(content);
            })
            .catch((error) => {
                setMarkdownDialogueContent(`An error occurred while downloading the file: ${error.message}`);
                console.error(error);
            })
        }
    }

    return (
        <li className="break-all">
            {reference.type} <a href={reference.url} target="_blank" rel="noopener noreferrer" onClick={openReference}>
                {reference.file}
            </a>
        </li>
    )
}


export default function Messages() {
    const { chatMessages, isFloating, isThinking } = useChatStore(useShallow((state) => ({
        chatMessages: state.chatMessages,
        isFloating: state.isFloating,
        isThinking: state.isThinking
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
                                    {message.references?.length && (
                                        <ul className="mt-2">
                                            {message.references.map((reference) => (
                                                <ReferenceDisplay key={reference.url} reference={reference} />
                                            ))}
                                        </ul>
                                    )}
                                </div>
                            </div>
                        ))}
                        {isThinking && <ThinkingIndicator />}
                    </div>
                </div>
            </div>
        </div>
    )
}