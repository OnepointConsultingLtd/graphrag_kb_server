export const MessageType = {
    ERROR: "ERROR",
    INFO: "INFO",
    WARNING: "WARNING",
    SUCCESS: "SUCCESS",
    QUESTION: "QUESTION",
    ANSWER: "ANSWER",
} as const;

export type MessageType = typeof MessageType[keyof typeof MessageType];

export type Message = {
    code?: string;
    content: string;
    messageType: MessageType;
}
