export default function RenderLabel({
  label,
  htmlFor,
}: {
  label: string;
  htmlFor?: string | undefined;
}) {
  return (
    <label className="label" htmlFor={htmlFor ?? undefined}>
      <span className="label-text text-white">{label}</span>
    </label>
  );
}
