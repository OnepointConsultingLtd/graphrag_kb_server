import type { Project } from "./projectCategory";
import type { ChatMessage } from "./message";

export type Query = {
  jwt: string;
  question: string;
  project: Project;
  chatHistory: ChatMessage[];
  conversationId: string;
};
