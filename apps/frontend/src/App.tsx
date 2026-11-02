import { ChatWidget } from "./components/ChatWidget";
import { Icon } from "./components/Icon";
import { mockChatClient } from "./services/mockChatClient";

export function App() {
  return (
    <main className="app-shell">
      <div className="app-brand">
        <span className="app-brand__mark">
          <Icon name="music" size={20} />
        </span>
        <span>Empório da Música</span>
      </div>
      <ChatWidget client={mockChatClient} />
    </main>
  );
}
