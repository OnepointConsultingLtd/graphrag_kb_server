import { useShallow } from "zustand/shallow";
import useProjectSelectionStore from "../../../context/projectSelectionStore";
import RenderLabel from "./RenderLabel";

export default function FieldAdditionalInstructions() {
  const { additionalPromptInstructions, setAdditionalPromptInstructions } =
    useProjectSelectionStore(
      useShallow((state) => ({
        additionalPromptInstructions: state.additionalPromptInstructions,
        setAdditionalPromptInstructions: state.setAdditionalPromptInstructions,
      })),
    );

  return (
    <div>
      <RenderLabel label="Additional Instructions" />
      <textarea
        name="additionalPromptInstructions"
        id="additionalPromptInstructions"
        value={additionalPromptInstructions}
        placeholder="Enter additional instructions"
        onChange={(e) => setAdditionalPromptInstructions(e.target.value)}
        className="textarea textarea-primary w-full bg-gray-700 text-gray-400 min-h-[100px]"
      >
        {additionalPromptInstructions || "No additional instructions"}
      </textarea>
    </div>
  );
}
