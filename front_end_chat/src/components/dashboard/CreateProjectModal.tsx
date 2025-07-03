import React, { useRef } from "react";
import { useShallow } from "zustand/react/shallow";
import { ENGINE_OPTIONS, ENGINES } from "../../constants/engines";
import useChatStore from "../../context/chatStore";
import { useDashboardStore } from "../../context/dashboardStore";
import { uploadIndex } from "../../lib/apiClient";
import { Engine, ModalType } from "../../types/types";
import RenderLabel from "./Form/RenderLabel";
import Modal from "./Modal";

export default function CreateProjectModal() {
  const {
    isModalOpen,
    modalType,
    projectName,
    engine,
    incremental,
    file,
    isSubmitting,
    error,
    uploadSuccessMessage,
    closeModal,
    setProjectName,
    setEngine,
    setIncremental,
    setFile,
    setIsSubmitting,
    setError,
    resetCreateProjectForm,
    setUploadSuccessMessage,
  } = useDashboardStore();

  const { jwt, refreshProjects } = useChatStore(
    useShallow((state) => ({ jwt: state.jwt, refreshProjects: state.refreshProjects }))
  );

  const fileInputRef = useRef<HTMLInputElement>(null);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  };

  function resetForm() {
    resetCreateProjectForm();
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  function handleClose() {
    resetForm();
    closeModal();
  };

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file || !projectName) {
      setError("Project name and file are required.");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("project", projectName);
    formData.append("engine", engine);
    formData.append("incremental", String(incremental));
    formData.append("asynchronous", "true");

    try {
      await uploadIndex(jwt, formData);
      refreshProjects();
      setUploadSuccessMessage(`Index (${projectName}) uploaded successfully. Please wait for the index to be ready.`);
      resetForm();
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("An unexpected error occurred.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isModalOpen && modalType === ModalType.CREATE || modalType === ModalType.UPDATE}
      title={modalType === ModalType.CREATE ? "Create New Project" : "Update Project"}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="label">
            <span className="label-text text-white">
              Project Name
            </span>
          </label>
          {modalType === ModalType.CREATE ? <input
            type="text"
            placeholder="The name of the project"
            className="input input-bordered w-full bg-gray-700"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            required
          /> : <div className="text-gray-400">{projectName}</div>}
        </div>

        <div>
          <RenderLabel label="Engine" />
          <select
            className="select select-bordered w-full bg-gray-700"
            value={engine}
            onChange={(e) => setEngine(e.target.value as Engine)}
          >
            {ENGINE_OPTIONS.filter((option) => modalType === ModalType.CREATE ? true : option.value === ENGINES.LIGHTRAG).map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <p className="text-xs text-gray-500 mt-1">
            The type of engine used to run the RAG system.
          </p>
        </div>

        {engine === ENGINES.LIGHTRAG && modalType === ModalType.UPDATE && <div>
          <RenderLabel label="Incremental Update" />
          <select
            className="select select-bordered w-full bg-gray-700"
            value={String(incremental)}
            onChange={(e) => setIncremental(e.target.value === "true")}
          >
            <option value="false">False</option>
            <option value="true">True</option>
          </select>
          <p className="text-xs text-gray-500 mt-1">
            Whether to update the existing index or create a new one. Works only
            for LightRAG.
          </p>
        </div>}

        <div>
          <RenderLabel label="Upload ZIP File" />
          <div className="w-full">
            <input
              type="file"
              ref={fileInputRef}
              className="file-input file-input-bordered w-full bg-gray-700"
              onChange={handleFileChange}
              accept=".zip"
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              The zip file with text, markdown or PDF files to be uploaded.
            </p>
          </div>
        </div>

        {error && <div className="alert alert-error">{error}</div>}
        {uploadSuccessMessage && <div className="alert alert-success">{uploadSuccessMessage}</div>}

        <div className="modal-action mt-6">
          <button
            type="button"
            onClick={handleClose}
            className="btn btn-ghost"
            disabled={isSubmitting}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={isSubmitting || !file || !projectName}
          >
            {isSubmitting ? (
              <span className="loading loading-spinner"></span>
            ) : (
              "Execute"
            )}
          </button>
        </div>
      </form>
    </Modal>
  );
}
