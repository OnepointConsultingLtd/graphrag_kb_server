import { FaCode, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { useShallow } from "zustand/shallow";
import useChatStore from "../../context/chatStore";
import { useDashboardStore } from "../../context/dashboardStore";
import useProjectSelectionStore from "../../context/projectSelectionStore";
import { ModalType } from "../../model/types";

export default function Actions() {
  const { openModal, openModalWithProject } = useDashboardStore();
  const selectionProject = useProjectSelectionStore(
    useShallow((state) => state.selectionProject),
  );

  const { selectedProject } = useChatStore(
    useShallow((state) => ({
      selectedProject: state.selectedProject,
    })),
  );

  const isActionDisabled = !selectionProject;
  const isLighrag = selectedProject?.platform === "lightrag";

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      <button
        onClick={() => openModal(ModalType.CREATE)}
        className="btn btn-primary btn-lg w-full group hover:scale-105 transition-transform"
      >
        <FaPlus className="mr-2 group-hover:rotate-90 transition-transform" />
        Create New Project
      </button>

      <button
        onClick={() => openModal(ModalType.SNIPPET)}
        disabled={isActionDisabled}
        className="btn btn-secondary btn-lg w-full group hover:scale-105 transition-transform disabled:opacity-50"
      >
        <FaCode className="mr-2 group-hover:animate-pulse" />
        Generate Snippets
      </button>

      <button
        onClick={() => openModalWithProject(ModalType.UPDATE, selectionProject)}
        disabled={isActionDisabled || !isLighrag}
        className="btn btn-accent btn-lg w-full group hover:scale-105 transition-transform disabled:opacity-50"
      >
        <FaEdit className="mr-2 group-hover:rotate-12 transition-transform" />
        Update Project
      </button>

      <button
        onClick={() => openModal(ModalType.DELETE)}
        disabled={isActionDisabled}
        className="btn btn-error btn-lg w-full group hover:scale-105 transition-transform disabled:opacity-50"
      >
        <FaTrash className="mr-2 group-hover:animate-bounce" />
        Delete Project
      </button>
    </div>
  );
}
