import { FaCode, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { useShallow } from "zustand/shallow";
import { useDashboardStore } from "../../context/dashboardStore";
import useProjectSelectionStore from "../../context/projectSelectionStore";

export default function Actions() {
  const { openModal } = useDashboardStore();
  const { selectionProject } = useProjectSelectionStore(
    useShallow((state) => ({
      selectionProject: state.selectionProject,
    }))
  );
  const isActionDisabled = !selectionProject;

  const handleUpdateProjects = () => {
    console.log("Update projects:", selectionProject);
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      <button
        onClick={() => openModal("create")}
        className="btn btn-primary btn-lg w-full group hover:scale-105 transition-transform"
      >
        <FaPlus className="mr-2 group-hover:rotate-90 transition-transform" />
        Create New Project
      </button>

      <button
        onClick={() => openModal("snippet")}
        disabled={isActionDisabled}
        className="btn btn-secondary btn-lg w-full group hover:scale-105 transition-transform disabled:opacity-50"
      >
        <FaCode className="mr-2 group-hover:animate-pulse" />
        Generate Snippets
      </button>

      <button
        onClick={handleUpdateProjects}
        disabled={isActionDisabled}
        className="btn btn-accent btn-lg w-full group hover:scale-105 transition-transform disabled:opacity-50"
      >
        <FaEdit className="mr-2 group-hover:rotate-12 transition-transform" />
        Update Projects
      </button>

      <button
        disabled={isActionDisabled}
        className="btn btn-error btn-lg w-full group hover:scale-105 transition-transform disabled:opacity-50"
      >
        <FaTrash className="mr-2 group-hover:animate-bounce" />
        Delete Projects
      </button>
    </div>
  );
}
