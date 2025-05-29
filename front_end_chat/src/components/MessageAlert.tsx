import type { Message } from "../model/message";
import { MessageType } from "../model/message";

function getAlertClass(messageType: MessageType) {
    switch (messageType) {
        case MessageType.ERROR:
            return "error";
        case MessageType.WARNING:
            return "warning";
        case MessageType.SUCCESS:
            return "success";
        case MessageType.INFO:
        case MessageType.ANSWER:
        case MessageType.QUESTION:
            return "info";
        default:
            return "info";
    }
}

export default function MessageAlert({ message }: { message: Message | null }) {
    if (!message) {
        return null;
    }
    return (
        <>
            <div role="alert" className={`w-full alert alert-dash alert-${getAlertClass(message.messageType)}`}>
                <span>{message.content}</span>
            </div>
        </>
    )
}