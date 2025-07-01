import { IoChatbubbleEllipsesOutline } from "react-icons/io5";

export default function FloatingChatButton({ click }: { click: () => void }) {
  return (
    <div
      className="fixed bottom-8 right-8 z-50 group cursor-pointer"
      onClick={click}
    >
      <div className="relative">
        <div className="absolute -inset-1 bg-gradient-to-r from-purple-600 to-blue-600 rounded-full blur opacity-75 group-hover:opacity-100 transition duration-300 animate-pulse"></div>
        <div className="relative bg-gradient-to-r from-blue-600 to-purple-600 text-white p-4 rounded-full shadow-2xl hover:shadow-purple-500/25 transition-all duration-300 hover:scale-110">
          <IoChatbubbleEllipsesOutline className="w-6 h-6" />
        </div>
      </div>
      <div className="absolute -top-10 -right-5 bg-black text-white px-3 py-1 rounded-lg text-sm opacity-0 group-hover:opacity-100 transition-opacity duration-300 whitespace-nowrap">
        Start chatting
      </div>
    </div>
  );
}
