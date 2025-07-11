import type { Reference } from "./references";

export const MessageType = {
  ERROR: "ERROR",
  INFO: "INFO",
  WARNING: "WARNING",
  SUCCESS: "SUCCESS",
  QUESTION: "QUESTION",
  ANSWER: "ANSWER",
} as const;

export type MessageType = (typeof MessageType)[keyof typeof MessageType];

export type ServerMessage = {
  code?: string;
  content: string;
  messageType: MessageType;
};

export const ChatMessageTypeOptions = {
  USER: "USER",
  AGENT: "AGENT",
  AGENT_ERROR: "AGENT_ERROR",
} as const;

export type ChatMessageType =
  (typeof ChatMessageTypeOptions)[keyof typeof ChatMessageTypeOptions];

export type ChatMessage = {
  id: string;
  text: string;
  type: ChatMessageType;
  timestamp: Date;
  conversationId?: string;
  references?: Reference[];
};

export type EntityContextEntry = {
  id: number;
  entity: string;
  type: string;
  description: string;
  rank: number;
  created_at: string;
  file_path: string;
};

export type StructuredQueryResponse = {
  response: string;
  references: Reference[];
};

export type QueryResponse = {
  response: StructuredQueryResponse;
  sources: string[];
  entities_context: EntityContextEntry[];
};
