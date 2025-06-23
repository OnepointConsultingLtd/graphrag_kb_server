import React from "react";
import { FaCopy } from "react-icons/fa";
import { useDashboardStore } from "../../context/dashboardStore";
import Modal from "./Modal";
import RenderLabel from "./Form/RenderLabel";

export default function GenerateSnippetModal() {
  const {
    modalType,
    closeModal,
    getSelectedProjects,
    email,
    setEmail,
    widgetType,
    setWidgetType,
    rootElementId,
    setRootElementId,
    organisationName,
    setOrganisationName,
    searchType,
    setSearchType,
    additionalPromptInstructions,
    setAdditionalPromptInstructions,
    isSnippetSubmitting,
    setIsSnippetSubmitting,
    snippetError,
    setSnippetError,
    generatedSnippet,
    setGeneratedSnippet,
  } = useDashboardStore();
  const selectedProjects = getSelectedProjects();

  const resetForm = () => {
    setGeneratedSnippet(null);
    setSnippetError(null);
  };

  const handleClose = () => {
    resetForm();
    closeModal();
  };

  const handleCopyToClipboard = () => {
    if (generatedSnippet) {
      navigator.clipboard.writeText(generatedSnippet);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSnippetSubmitting(true);
    setSnippetError(null);
    setGeneratedSnippet(null);

    const project = selectedProjects[0];
    if (!project) {
      setSnippetError("No project selected.");
      setIsSnippetSubmitting(false);
      return;
    }

    const requestBody = {
      email,
      widget_type: widgetType,
      root_element_id: rootElementId,
      jwt: "string",
      organisation_name: organisationName,
      project: {
        name: project.name,
        search_type: searchType,
        platform: project.engine,
        additional_prompt_instructions: additionalPromptInstructions,
      },
    };

    try {
      const response = await fetch(
        "http://localhost:9999/protected/snippet/generate_snippet",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(requestBody),
        }
      );

      const responseData = await response.json();

      if (!response.ok) {
        throw new Error(
          responseData.description || `HTTP error! status: ${response.status}`
        );
      }

      setGeneratedSnippet(responseData.snippet);
    } catch (err) {
      if (err instanceof Error) {
        setSnippetError(err.message);
      } else {
        setSnippetError("An unexpected error occurred.");
      }
    } finally {
      setIsSnippetSubmitting(false);
    }
  };

  return (
    <Modal isOpen={modalType === "snippet"} title="Generate Snippet">
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Form Fields */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <RenderLabel label="Email" />
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="input input-bordered w-full bg-gray-700"
              required
            />
          </div>
          <div>
            <RenderLabel label="Organisation" />
            <input
              type="text"
              value={organisationName}
              onChange={(e) => setOrganisationName(e.target.value)}
              className="input input-bordered w-full bg-gray-700"
              required
            />
          </div>
          <div>
            <RenderLabel label="Widget Type" />
            <select
              value={widgetType}
              onChange={(e) => setWidgetType(e.target.value)}
              className="select select-bordered w-full bg-gray-700"
            >
              <option>FLOATING_CHAT</option>
              <option>FULL_PAGE</option>
            </select>
          </div>
          <div>
            <RenderLabel label="Search Type" />
            <select
              value={searchType}
              onChange={(e) => setSearchType(e.target.value)}
              className="select select-bordered w-full bg-gray-700"
            >
              <option>local</option>
              <option>global</option>
            </select>
          </div>
        </div>

        {/* Root Element ID */}
        <div>
          <RenderLabel label="Root Element ID" />
          <input
            type="text"
            value={rootElementId}
            onChange={(e) => setRootElementId(e.target.value)}
            className="input input-bordered w-full bg-gray-700"
          />
        </div>
        {/* Additional Instructions */}
        <div>
          <RenderLabel label="Additional Instructions" />
          <textarea
            value={additionalPromptInstructions}
            onChange={(e) => setAdditionalPromptInstructions(e.target.value)}
            className="textarea textarea-bordered w-full bg-gray-700"
          />
        </div>

        {/* Error */}
        {snippetError && (
          <div className="alert alert-error">{snippetError}</div>
        )}

        {/* Generated Snippet */}
        {generatedSnippet && (
          <div className="space-y-2">
            <h4 className="font-semibold">Generated Snippet:</h4>
            <div className="relative bg-gray-900 rounded-lg p-4 font-mono text-sm">
              <button
                type="button"
                onClick={handleCopyToClipboard}
                className="absolute top-2 right-2 btn btn-xs btn-ghost"
              >
                <FaCopy />
              </button>
              <pre>
                <code>{generatedSnippet}</code>
              </pre>
            </div>
          </div>
        )}

        <div className="modal-action mt-6">
          <button
            type="button"
            onClick={() => handleClose()}
            className="btn btn-ghost"
            disabled={isSnippetSubmitting}
          >
            Close
          </button>
          <button
            type="submit"
            className="btn btn-secondary"
            disabled={isSnippetSubmitting || selectedProjects.length === 0}
          >
            {isSnippetSubmitting ? (
              <span className="loading loading-spinner"></span>
            ) : (
              "Generate"
            )}
          </button>
        </div>
      </form>
    </Modal>
  );
}
