import { ChatMessageTypeOptions } from "../model/message";

export function createChatMessage(text: string, conversationId: string | null) {
    return {
        id: crypto.randomUUID(),
        text,
        type: ChatMessageTypeOptions.AGENT,
        timestamp: new Date(),
        ...(conversationId ? { conversationId: conversationId } : {}),
        references: [],
    };
}