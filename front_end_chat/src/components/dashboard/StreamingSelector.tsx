import { useShallow } from "zustand/react/shallow";
import useChatStore from "../../context/chatStore";
import useProjectSelectionStore from "../../context/projectSelectionStore";

export function StreamingSelector() {
  const { selectionPlatform } = useProjectSelectionStore(
    useShallow((state) => ({
      selectionPlatform: state.selectionPlatform,
    }))
  );

  const { useStreaming, setUseStreaming } = useChatStore(
    useShallow((state) => ({
      useStreaming: state.useStreaming,
      setUseStreaming: state.setUseStreaming,
    }))
  );

  if (selectionPlatform === "lightrag") {
    return null;
  }

  return (
    <div className="mb-6">
      <label
        className="block text-sm font-medium text-gray-300 mb-2"
        htmlFor="streaming"
      >
        Streaming
      </label>
      <input
        type="checkbox"
        id="streaming"
        checked={useStreaming}
        onChange={() => setUseStreaming(!useStreaming)}
      />
    </div>
  );
}
