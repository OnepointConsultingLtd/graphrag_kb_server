import { FaCopy } from "react-icons/fa";

export default function CopyToClipboard({
  handleCopyToClipboard,
  className,
}: {
  handleCopyToClipboard: () => void;
  className?: string;
}) {
  return (
    <button
      type="button"
      onClick={handleCopyToClipboard}
      className={`top-2 right-2 btn btn-xs btn-ghost`}
      title="Copy to clipboard"
    >
      <FaCopy className={className} />
    </button>
  );
}
