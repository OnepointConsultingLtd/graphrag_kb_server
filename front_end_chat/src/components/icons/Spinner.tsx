export default function Spinner({ size = 16 }: { size?: number }) {
  const dotSize = Math.max(Math.round(size / 4), 4);
  const ringSize = size;

  return (
    <div className="relative flex items-center justify-center mx-auto mb-6" style={{ width: `${ringSize * 4}px`, height: `${ringSize * 4}px` }}>
      {/* Outer ring */}
      <div
        className="absolute rounded-full border-2 border-[#0992C2]/30 breathing-ring"
        style={{ width: `${ringSize * 4}px`, height: `${ringSize * 4}px` }}
      />
      {/* Inner dot */}
      <div
        className="rounded-full bg-gradient-to-br from-[#0992C2] to-[#066a8f] shadow-lg shadow-[#0992C2]/40 breathing-dot"
        style={{ width: `${dotSize * 4}px`, height: `${dotSize * 4}px` }}
      />
    </div>
  );
}
