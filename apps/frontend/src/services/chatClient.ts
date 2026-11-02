export type ChatClient = {
  sendMessage: (message: string, options?: { retry?: boolean }) => Promise<string>;
};
