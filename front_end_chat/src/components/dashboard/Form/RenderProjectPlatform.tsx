import { useShallow } from "zustand/shallow";
import RenderLabel from "./RenderLabel";
import useProjectSelectionStore from "../../../context/projectSelectionStore";


export default function RenderProjectPlatform() {
    const { selectionProject, selectionPlatform } = useProjectSelectionStore(
        useShallow((state) => ({
            selectionProject: state.selectionProject,
            selectionPlatform: state.selectionPlatform,
        })),
    );
    return <div className="flex flex-row gap-2 justify-between">
        <div>
            <RenderLabel label="Project" />
            <p className="text-gray-400 ">{selectionProject}</p>
        </div>
        <div>
            <RenderLabel label="Platform" />
            <p className="text-gray-400 ">{selectionPlatform}</p>
        </div>
    </div>;
}