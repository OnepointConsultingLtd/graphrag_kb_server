import Header from "./Header";
import Messages from "./Messages";
import ChatInput from "./ChatInput";

export default function ChatContainer() {
  return (
    <main className="flex h-screen">
      <div className="flex flex-col flex-1">
        {/* Header */}
        <div className="flex items-center border-b border-[#e2e8f0] backdrop-blur-lg sticky top-0 z-[100]">
          <Header />
        </div>
        <Messages />
        <ChatInput />
      </div>
    </main>
  );
}
