export default function MessageTimestamp({ timestamp }: { timestamp: string }) {
  return (
    <div className="ml-2 text-xs">
      {new Date(timestamp).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      })}
    </div>
  );
}
