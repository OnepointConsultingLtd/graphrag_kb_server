import type { Project } from "./projectCategory";
import type { ChatMessage } from "./message";
import type { Engine } from "./types";

export type Query = {
  jwt: string;
  question: string;
  project: Project;
  chatHistory: ChatMessage[];
  conversationId: string;
};

// Context Parameters type
export type ContextParameters = {
  query: string;
  project_dir: string; // Using string instead of Path for frontend
  context_size: number;
};

// Chat history message type
export type ChatHistoryMessage = {
  role: string;
  content: string;
};

// Query Parameters type
export type QueryParameters = {
  format: string;
  search: string;
  engine: Engine;
  context_params: ContextParameters;
  systemPrompt?: string | null;
  systemPromptAdditional?: string | null;
  hlKeywords: string[];
  llKeywords: string[];
  includeContext: boolean;
  includeContextAsText: boolean;
  structuredOutput: boolean;
  chatHistory: ChatHistoryMessage[];
  conversationId: string;
  stream: boolean;
};

export function convertQueryToQueryParameters(query: Query): QueryParameters {
  return {
    format: "json",
    search: query.project.search_type,
    engine: query.project.platform,
    context_params: {
      query: query.question,
      project_dir: "",
      context_size: 8000,
    },
    systemPrompt: query.project.additional_prompt_instructions,
    systemPromptAdditional: "",
    hlKeywords: [],
    llKeywords: [],
    includeContext: false,
    includeContextAsText: false,
    structuredOutput: false,
    chatHistory: [],
    conversationId: query.conversationId,
    stream: true,
  };
}
