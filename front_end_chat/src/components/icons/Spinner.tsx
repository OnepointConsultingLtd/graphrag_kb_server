export default function Spinner({ size = 16 }: { size?: number }) {
  return (
    <div className="relative mb-6">
      <div className={`w-${size} h-${size} border-4 border-gray-700 border-t-blue-500 rounded-full animate-spin mx-auto`}></div>
      <div className="absolute inset-0 w-16 h-16 border-4 border-transparent border-t-blue-400 rounded-full animate-ping mx-auto"></div>
    </div>
  );
}
