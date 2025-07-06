import React from "react";
import { FaCopy } from "react-icons/fa";
import { useShallow } from "zustand/shallow";
import useChatStore from "../../context/chatStore";
import { useDashboardStore } from "../../context/dashboardStore";
import useProjectSelectionStore from "../../context/projectSelectionStore";
import RenderLabel from "./Form/RenderLabel";
import SelectSearchEngine from "./SelectSearchEngine";
import { generateSnippet } from "../../lib/apiClient";
import FieldEmail from "./Form/FieldEmail";
import FieldWidgetType from "./Form/FieldWidgetType";

export const GENERATE_SNIPPET_MODAL_ID = "generate-snippet-modal";

export default function GenerateSnippetModal() {
  const {
    closeModal,
    email,
    rootElementId,
    setRootElementId,
    organisationName,
    setOrganisationName,
    snippetError,
    setSnippetError,
    generatedSnippet,
    isSnippetSubmitting,
    setIsSnippetSubmitting,
    setGeneratedSnippet,
    widgetType,
  } = useDashboardStore(
    useShallow((state) => ({
      closeModal: state.closeModal,
      email: state.email,
      setEmail: state.setEmail,
      setRootElementId: state.setRootElementId,
      rootElementId: state.rootElementId,
      organisationName: state.organisationName,
      setOrganisationName: state.setOrganisationName,
      snippetError: state.snippetError,
      setSnippetError: state.setSnippetError,
      generatedSnippet: state.generatedSnippet,
      isSnippetSubmitting: state.isSnippetSubmitting,
      setIsSnippetSubmitting: state.setIsSnippetSubmitting,
      setGeneratedSnippet: state.setGeneratedSnippet,
      widgetType: state.widgetType,
    })),
  );

  const { jwt, organisation_name } = useChatStore(
    useShallow((state) => ({
      jwt: state.jwt,
      organisation_name: state.organisation_name,
    })),
  );

  const {
    selectionProject,
    searchType,
    selectionPlatform,
    additionalPromptInstructions,
    setAdditionalPromptInstructions,
  } = useProjectSelectionStore(
    useShallow((state) => ({
      selectionProject: state.selectionProject,
      searchType: state.searchType,
      selectionPlatform: state.selectionPlatform,
      additionalPromptInstructions: state.additionalPromptInstructions,
      setAdditionalPromptInstructions: state.setAdditionalPromptInstructions,
    })),
  );

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

    if (!selectionProject) {
      setSnippetError("No project selected.");
      setIsSnippetSubmitting(false);
      return;
    }

    const requestBody = {
      email,
      widget_type: widgetType,
      root_element_id: rootElementId,
      jwt: jwt,
      organisation_name: organisationName || organisation_name,
      project: {
        name: selectionProject,
        search_type: searchType,
        platform: selectionPlatform,
        additional_prompt_instructions: additionalPromptInstructions,
      },
    };

    try {
      const responseData = await generateSnippet(jwt, requestBody);

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
    <dialog id={GENERATE_SNIPPET_MODAL_ID} title="Generate Snippet" className="modal">
      <form onSubmit={handleSubmit} className="space-y-4 bg-gray-800 rounded-lg p-6 w-full max-w-lg mx-4">
        {/* Form Fields */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FieldEmail />
          <div>
            <RenderLabel label="Organisation" />
            <input
              type="text"
              value={organisationName}
              onChange={(e) => setOrganisationName(e.target.value)}
              className="input input-primary w-full bg-gray-700"
              required
            />
          </div>
          <FieldWidgetType />
          <div>
            <RenderLabel label="Search Type" />
            <SelectSearchEngine />
          </div>
        </div>

        {/* Root Element ID */}
        <div>
          <RenderLabel label="Root Element ID" />
          <input
            type="text"
            value={rootElementId}
            onChange={(e) => setRootElementId(e.target.value)}
            className="input input-primary w-full bg-gray-700"
          />
        </div>

        {/* Project */}
        <div>
          <RenderLabel label="Project" />
          <p className="text-gray-400 ">{selectionProject}</p>
        </div>

        {/* Platform */}
        <div>
          <RenderLabel label="Platform" />
          <p className="text-gray-400 ">{selectionPlatform}</p>
        </div>

        {/* Additional Instructions */}
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
              <pre className="overflow-x-auto">
                <code className="whitespace-pre-wrap">{generatedSnippet}</code>
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
            disabled={isSnippetSubmitting || !selectionProject}
          >
            {isSnippetSubmitting ? (
              <span className="loading loading-spinner"></span>
            ) : (
              "Generate"
            )}
          </button>
        </div>
      </form>
    </dialog>
  );
}
