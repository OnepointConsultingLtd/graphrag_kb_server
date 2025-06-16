import { useEffect, useState } from "react";
import {
  IoArrowForwardOutline,
  IoFlashOutline,
  IoSparklesOutline,
} from "react-icons/io5";
import FloatingChatButton from "./components/FloatingChat/FloatingChatButton";
import FloatingChatMain from "./components/FloatingChat/FloatingChatMain";

const FloatingChat = () => {
  const [isFloatingOpen, setIsFloatingOpen] = useState(false);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    setIsVisible(true);
  }, []);

  const handleFloatingBtn = () => {
    setIsFloatingOpen(!isFloatingOpen);
  };

  return (
    <div className="min-h-screen !w-full max-w-full bg-gradient-to-br ">
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-purple-300 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-yellow-300 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob animation-delay-2000"></div>
        <div className="absolute top-40 left-40 w-80 h-80 bg-pink-300 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob animation-delay-4000"></div>
      </div>

      <div className="relative z-10 w-full !max-w-full">
        {/* Hero Section */}
        <div
          className={`min-h-screen flex flex-col items-center justify-center px-4 transition-all duration-1000 ${
            isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-10"
          }`}
        >
          <div className="text-center max-w-full mx-auto">
            <div className="inline-flex items-center bg-white/80 backdrop-blur-sm border border-white/30 rounded-full px-6 py-2 mb-8 shadow-lg">
              <IoSparklesOutline className="w-4 h-4 text-purple-600 mr-2" />
              <span className="text-sm font-medium text-gray-700">
                Powered by Advanced AI Technology
              </span>
            </div>

            <h1 className="text-6xl md:text-7xl lg:text-8xl font-black bg-gradient-to-r from-blue-600 via-purple-600 to-indigo-600 bg-clip-text text-transparent mb-6 leading-tight">
              Welcome to
              <br />
              <span className="relative text-gray-400">
                Onepoint Chat
                <div className="absolute -bottom-2 left-0 right-0 h-1 bg-gradient-to-r from-blue-600 to-purple-600 rounded-full"></div>
              </span>
            </h1>

            <p className="text-xl md:text-2xl text-gray-100 mb-4 font-light leading-relaxed">
              Your private document intelligence platform powered by our Rag
              System.
            </p>

            <p className="text-lg text-gray-200 mb-12 max-w-2xl mx-auto leading-relaxed">
              Upload your documents, let our AI index and understand them, then
              chat naturally with your own knowledge base. Secure, private, and
              built for your personal document intelligence needs.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-16">
              <button
                onClick={handleFloatingBtn}
                className="cursor-pointer group bg-gradient-to-r from-blue-600 to-purple-600 text-white px-8 py-4 rounded-full text-lg font-semibold hover:shadow-2xl hover:shadow-purple-500/25 transition-all duration-300 hover:scale-105 flex items-center space-x-2"
              >
                <span>Start Chatting Now</span>
                <IoArrowForwardOutline className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </button>

              <button className="cursor-pointer group border-2 border-gray-300 text-gray-700 px-8 py-4 rounded-full text-lg font-semibold hover:border-purple-400 hover:text-purple-600 transition-all duration-300 flex items-center space-x-2">
                <span>Learn More</span>
                <IoFlashOutline className="w-5 h-5 group-hover:rotate-12 transition-transform" />
              </button>
            </div>
          </div>
        </div>

        {/* Floating Chat */}
        {isFloatingOpen ? (
          <div className="absolute lg:fixed bottom-10 right-8 z-50">
            <FloatingChatMain handleFloatingBtn={handleFloatingBtn} />
          </div>
        ) : (
          <FloatingChatButton click={handleFloatingBtn} />
        )}
      </div>
    </div>
  );
};

export default FloatingChat;
