type AlertType = "error" | "success" | "warning" | "info";

export default function FormAlert({
  message,
  type = "error",
}: {
  message: string | null | undefined;
  type?: AlertType;
}) {
  if (!message) return null;

  return <div className={`alert alert-${type} mt-3`}>{message}</div>;
}
