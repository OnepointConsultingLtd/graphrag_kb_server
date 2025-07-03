import { useState } from "react";
import { FaCheck, FaExclamationTriangle, FaSpinner } from "react-icons/fa";
import { useShallow } from "zustand/react/shallow";
import useChatStore from "../../context/chatStore";
import { useDashboardStore } from "../../context/dashboardStore";
import useProjectSelectionStore from "../../context/projectSelectionStore";
import { deleteProject } from "../../lib/apiClient";
import { ModalType } from "../../model/types";
import Modal from "./Modal";

export default function DeleteConfirmation() {
  const {
    isModalOpen,
    modalType,
    closeModal,
    success,
    error,
    setSuccess,
    setError,
  } = useDashboardStore();

  const { jwt, refreshProjects } = useChatStore(
    useShallow((state) => ({
      jwt: state.jwt,
      refreshProjects: state.refreshProjects,
    })),
  );

  const { selectionProject, selectionPlatform, setSelectionProject } =
    useProjectSelectionStore(
      useShallow((state) => ({
        selectionProject: state.selectionProject,
        selectionPlatform: state.selectionPlatform,
        setSelectionProject: state.setSelectionProject,
      })),
    );

  const [isDeleting, setIsDeleting] = useState(false);

  const handleDeleteProject = async () => {
    if (!selectionProject) {
      setError("No project selected for deletion");
      return;
    }

    if (!selectionPlatform) {
      setError("Project platform not found");
      return;
    }

    setIsDeleting(true);
    setError(null);

    try {
      await deleteProject(jwt, selectionProject, selectionPlatform);
      await refreshProjects();

      setTimeout(() => {
        setSelectionProject("");
        closeModal();
        setSuccess(null);
      }, 1500);
    } catch (error) {
      setError(`Failed to delete project. Please try again. - ${error}`);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleCancel = () => {
    setError(null);
    setSuccess(null);
    closeModal();
  };

  return (
    <Modal
      isOpen={isModalOpen && modalType === ModalType.DELETE}
      title="Delete Project"
    >
      <div className="space-y-6">
        {/* Success Message */}
        {success && (
          <div className="alert alert-success">
            <FaCheck />
            <span>{success}</span>
          </div>
        )}

        {/* Warning Icon and Message */}
        {!success && (
          <div className="flex items-center space-x-3 p-4 bg-red-900/20 border border-red-500/30 rounded-lg">
            <FaExclamationTriangle className="text-red-400 text-xl flex-shrink-0" />
            <div>
              <h4 className="font-semibold text-red-400">Warning</h4>
              <p className="text-sm text-gray-300">
                This action cannot be undone. The project and all its data will
                be permanently deleted.
              </p>
            </div>
          </div>
        )}

        {/* Project Details */}
        {!success && (
          <div className="bg-gray-800/50 p-4 rounded-lg">
            <h4 className="font-medium text-gray-200 mb-2">
              Project to be deleted:
            </h4>
            <div className="space-y-1">
              <p className="text-lg font-semibold text-white">
                {selectionProject || "No project selected"}
              </p>
              {selectionPlatform && (
                <p className="text-sm text-gray-400">
                  Platform: {selectionPlatform}
                </p>
              )}
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="alert alert-error">
            <FaExclamationTriangle />
            <span>{error}</span>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex justify-end space-x-3 pt-4">
          {!success && (
            <button
              onClick={handleCancel}
              className="btn btn-ghost"
              disabled={isDeleting}
            >
              Cancel
            </button>
          )}

          {!success && (
            <button
              onClick={handleDeleteProject}
              className="btn btn-error"
              disabled={isDeleting || !selectionProject}
            >
              {isDeleting ? (
                <>
                  <FaSpinner className="animate-spin mr-2" />
                  Deleting...
                </>
              ) : (
                "Delete Project"
              )}
            </button>
          )}
        </div>
      </div>
    </Modal>
  );
}
