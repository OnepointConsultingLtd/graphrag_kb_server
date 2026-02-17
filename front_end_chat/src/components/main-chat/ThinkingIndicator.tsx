export default function ThinkingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="flex items-center gap-3 px-2 py-3">
        <div className="relative flex items-center justify-center w-10 h-10">
          {/* Outer ring */}
          <div className="absolute w-10 h-10 rounded-full border-2 border-[#0992C2]/30 breathing-ring" />
          {/* Inner dot */}
          <div className="w-4 h-4 rounded-full bg-gradient-to-br from-[#0992C2] to-[#066a8f] shadow-lg shadow-[#0992C2]/40 breathing-dot" />
        </div>
        <span className="text-sm text-gray-400 font-medium tracking-wide">
          Thinking...
        </span>
      </div>
    </div>
  );
}
