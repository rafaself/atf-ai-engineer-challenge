export type ChatResponse = {
  answer: string;
  session_id: string;
};

export type ConversationSummary = {
  session_id: string;
  title: string;
};

export type ConversationMessage = {
  role: "user" | "assistant";
  content: string;
};

export type ConversationTranscript = {
  session_id: string;
  messages: ConversationMessage[];
};

export type ChatClient = {
  streamMessage: (
    message: string,
    sessionId: string | undefined,
    onDelta: (text: string) => void,
  ) => Promise<ChatResponse>;
  listConversations: () => Promise<ConversationSummary[]>;
  getConversation: (sessionId: string) => Promise<ConversationTranscript>;
  deleteConversation: (sessionId: string) => Promise<void>;
};

export type ChatFailureState = "failed" | "unknown";

export class ChatClientError extends Error {
  constructor(
    message: string,
    readonly state: ChatFailureState,
  ) {
    super(message);
    this.name = "ChatClientError";
  }
}
