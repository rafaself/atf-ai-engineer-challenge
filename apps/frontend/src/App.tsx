import { ChatWidget } from "./components/ChatWidget";
import { Icon } from "./components/Icon";
import { httpChatClient } from "./services/httpChatClient";

export function App() {
  return (
    <main className="app-shell">
      <div className="app-brand">
        <span className="app-brand__mark">
          <Icon name="music" size={20} />
        </span>
        <span>Empório da Música</span>
      </div>
      <ChatWidget client={httpChatClient} />
      <p className="demo-notice">
        Demonstração com dados fictícios. As consultas simulam os sistemas da loja.
        <br />
        Para testar, pergunte sobre o código de rastreamento <strong>BRQM7890123BR</strong>.
      </p>
    </main>
  );
}
