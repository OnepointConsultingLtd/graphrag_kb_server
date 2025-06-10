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
            downloadFile(jwt, project, reference, false)
                .then((response) => response.text())
                .then((content) => {
                    setMarkdownDialogueContent(content);
                })
                .catch((error) => {
                    setMarkdownDialogueContent(`An error occurred while downloading the file: ${error.message}`);
                    console.error(error);
                })
        }
    }

    function openOriginal(e: React.MouseEvent<HTMLAnchorElement>) {
        e.preventDefault();
        if (project) {
            downloadFile(jwt, project, reference, true)
                .then((response) => Promise.all([response, response.blob()]))
                .then(([response, blob]) => {
                    const contentDisposition = response.headers.get('Content-Disposition');
                    let filename = 'downloaded_file';
                    if (contentDisposition) {
                        const filenameMatch = contentDisposition.match(/filename="([^"]+)"/);
                        if (filenameMatch && filenameMatch[1]) {
                            filename = filenameMatch[1];
                        }
                    }
                    // Create a Blob URL
                    const blobUrl = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = blobUrl;
                    a.download = filename; // Set the download attribute to suggest a filename

                    // Append the anchor to the body (it doesn't need to be visible)
                    document.body.appendChild(a);

                    // Programmatically click the anchor to trigger the download
                    a.click();

                    // Clean up: revoke the Blob URL after a short delay
                    // This is important to free up memory
                    setTimeout(() => {
                        URL.revokeObjectURL(blobUrl);
                        document.body.removeChild(a);
                    }, 100);
                })
                .catch((error) => {
                    setMarkdownDialogueContent(`An error occurred while downloading the original file: ${error.message}`);
                    console.error(error);
                })
        }
    }

    return (
        <li className="break-all flex">
            {reference.type} <a href={reference.url} target="_blank" rel="noopener noreferrer" onClick={openReference}>
                {reference.file}
            </a>
            <a href={reference.url} className="mt-1.5 ml-1" target="_blank" rel="noopener noreferrer" onClick={openOriginal}>
                <svg className="w-4 h-4" stroke="currentColor" fill="currentColor" strokeWidth="0" version="1.2" baseProfile="tiny" viewBox="0 0 24 24" height="60px" width="60px" xmlns="http://www.w3.org/2000/svg">
                    <g>
                        <path d="M17 21h-10c-1.654 0-3-1.346-3-3v-12c0-1.654 1.346-3 3-3h10c1.654 0 3 1.346 3 3v12c0 1.654-1.346 3-3 3zm-10-16c-.551 0-1 .449-1 1v12c0 .551.449 1 1 1h10c.551 0 1-.449 1-1v-12c0-.551-.449-1-1-1h-10zM16 11h-8c-.276 0-.5-.224-.5-.5s.224-.5.5-.5h8c.276 0 .5.224.5.5s-.224.5-.5.5zM16 8h-8c-.276 0-.5-.224-.5-.5s.224-.5.5-.5h8c.276 0 .5.224.5.5s-.224.5-.5.5zM16 14h-8c-.276 0-.5-.224-.5-.5s.224-.5.5-.5h8c.276 0 .5.224.5.5s-.224.5-.5.5zM16 17h-8c-.276 0-.5-.224-.5-.5s.224-.5.5-.5h8c.276 0 .5.224.5.5s-.224.5-.5.5z"></path>
                    </g>
                </svg>
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
                                    {message.references?.length && message.references.length > 0 ? (
                                        <ul className="mt-2">
                                            {message.references.map((reference) => (
                                                <ReferenceDisplay key={reference.url} reference={reference} />
                                            ))}
                                        </ul>
                                    ) : null}
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