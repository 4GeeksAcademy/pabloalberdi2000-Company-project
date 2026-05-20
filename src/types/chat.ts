export type ChatRole = "user" | "assistant";

export interface UsageMetadata {
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
  latencySeconds: number;
  model: string;
}

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: number;
  usage?: UsageMetadata;
}

export interface ChatSession {
  id: string;
  title: string;
  createdAt: number;
  messages: ChatMessage[];
}

export interface ChatSettings {
  temperature: number;
  topP: number;
  jsonMode: boolean;
}
