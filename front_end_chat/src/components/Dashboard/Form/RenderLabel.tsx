export default function RenderLabel({ label }: { label: string }) {
  return (
    <label className="label">
      <span className="label-text text-white">{label}</span>
    </label>
  );
}
