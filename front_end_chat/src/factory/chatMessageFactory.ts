import { ChatMessageTypeOptions } from "../model/message";
import { v4 as uuidv4 } from "uuid";

export function createChatMessage(text: string, conversationId: string | null) {
  return {
    id: uuidv4(),
    text,
    type: ChatMessageTypeOptions.AGENT,
    timestamp: new Date(),
    ...(conversationId ? { conversationId: conversationId } : {}),
    references: [],
  };
}
