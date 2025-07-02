export default function MessageTimestamp({ timestamp }: { timestamp: string }) {
  return (
    <div className="text-xs">
      {new Date(timestamp).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      })}
    </div>
  );
}
