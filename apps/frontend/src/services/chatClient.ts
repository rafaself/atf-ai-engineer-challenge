export type ChatResponse = {
  answer: string;
  session_id: string;
};

export type ChatClient = {
  sendMessage: (message: string, sessionId?: string) => Promise<ChatResponse>;
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
