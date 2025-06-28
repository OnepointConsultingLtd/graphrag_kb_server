import React, { useState } from "react";
import { FaCopy } from "react-icons/fa";
import { useShallow } from "zustand/shallow";
import useChatStore from "../../context/chatStore";
import { useDashboardStore } from "../../context/dashboardStore";
import useProjectSelectionStore from "../../context/projectSelectionStore";
import { getBaseServer } from "../../lib/server";
import RenderLabel from "./Form/RenderLabel";
import Modal from "./Modal";
import SelectSearchEngine from "./SelectSearchEngine";

export default function GenerateSnippetModal() {
  const {
    modalType,
    closeModal,
    email,
    setEmail,
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
  } = useDashboardStore(
    useShallow((state) => ({
      modalType: state.modalType,
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
    }))
  );

  const [widgetType, setWidgetType] = useState<string>("FLOATING_CHAT");

  const { jwt, organisation_name } = useChatStore(
    useShallow((state) => ({
      jwt: state.jwt,
      organisation_name: state.organisation_name,
    }))
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
    }))
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
      const response = await fetch(
        `${getBaseServer()}/protected/snippet/generate_snippet`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${jwt}`,
          },
          body: JSON.stringify(requestBody),
        }
      );

      const responseData = await response.json();

      console.log("Response data:", responseData);
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
              className="input input-primary w-full bg-gray-700"
              required
            />
          </div>
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
          <div>
            <RenderLabel label="Widget Type" />
            <select
              value={widgetType}
              onChange={(e) => setWidgetType(e.target.value)}
              className="select select-primary  w-full bg-gray-700"
            >
              <option>FLOATING_CHAT</option>
              <option>CHAT</option>
            </select>
          </div>
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
    </Modal>
  );
}
