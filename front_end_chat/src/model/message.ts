export const MessageType = {
    ERROR: "ERROR",
    INFO: "INFO",
    WARNING: "WARNING",
    SUCCESS: "SUCCESS",
    QUESTION: "QUESTION",
    ANSWER: "ANSWER",
} as const;

export type MessageType = typeof MessageType[keyof typeof MessageType];

export type ServerMessage = {
    code?: string;
    content: string;
    messageType: MessageType;
}

export enum ChatMessageType {
    USER = "user",
    AGENT = "agent",
    AGENT_ERROR = "agent_error"
}

export type ChatMessage = {
	id: string;
	text: string;
	type: ChatMessageType;
	timestamp: Date;
	conversationId?: string;
    references?: Reference[];
}

export type QueryResponse = {
    response: string;
    sources: string[];
}
