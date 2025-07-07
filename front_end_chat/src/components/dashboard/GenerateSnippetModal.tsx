import React from "react";
import AceEditor from "react-ace";
import { useShallow } from "zustand/shallow";
import useChatStore from "../../context/chatStore";
import { useDashboardStore } from "../../context/dashboardStore";
import useProjectSelectionStore from "../../context/projectSelectionStore";
import RenderLabel from "./Form/RenderLabel";
import { generateSnippet } from "../../lib/apiClient";
import FieldEmail from "./Form/FieldEmail";
import FieldWidgetType from "./Form/FieldWidgetType";
import ModalTitle from "./ModalTitle";
import FieldSearchType from "./Form/FieldSearchType";

// Import ace editor modes and themes
import "ace-builds/src-noconflict/mode-javascript";
import "ace-builds/src-noconflict/mode-html";
import "ace-builds/src-noconflict/mode-css";
import "ace-builds/src-noconflict/theme-monokai";
import "ace-builds/src-noconflict/ext-language_tools";
import RenderProjectPlatform from "./Form/RenderProjectPlatform";
import FieldAdditionalInstructions from "./Form/FieldAdditionalInstructions";
import ModalParent from "./ModalParent";
import CopyToClipboard from "../buttons/CopyToClipboard";

export const GENERATE_SNIPPET_MODAL_ID = "generate-snippet-modal";


export default function GenerateSnippetModal() {
  const {
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
    setSnippetModalDialogueOpen,
  } = useDashboardStore(
    useShallow((state) => ({
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
      setSnippetModalDialogueOpen: state.setSnippetModalDialogueOpen,
    }))
  );

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
    setSnippetModalDialogueOpen(false);
  };

  const handleReset = () => {
    resetForm();
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
    <ModalParent id={GENERATE_SNIPPET_MODAL_ID}>
      <form
        onSubmit={handleSubmit}
      >
        <ModalTitle title="Generate Snippet" />

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
          <FieldSearchType />
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

        <div className="grid grid-cols-1 gap-2 mt-2">
          {/* Project */}
          <RenderProjectPlatform />

          {/* Additional Instructions */}
          <FieldAdditionalInstructions />
        </div>

        {/* Error */}
        {snippetError && (
          <div className="alert alert-error">{snippetError}</div>
        )}

        {/* Generated Snippet */}
        {generatedSnippet && (
          <div className="space-y-2 relative">
            <div className="flex justify-between items-center">
              <h4 className="font-semibold">Generated Snippet: </h4>
              <CopyToClipboard handleCopyToClipboard={handleCopyToClipboard} />
            </div>
            <div className="relative bg-gray-900 rounded-lg p-4 font-mono text-sm">
              <AceEditor
                mode="html"
                theme="monokai"
                value={generatedSnippet}
                readOnly={true}
                width="100%"
                height="300px"
                showPrintMargin={false}
                showGutter={true}
                highlightActiveLine={false}
                setOptions={{
                  enableBasicAutocompletion: false,
                  enableLiveAutocompletion: false,
                  enableSnippets: false,
                  showLineNumbers: true,
                  tabSize: 2,
                }}
              />
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
            type="button"
            onClick={() => handleReset()}
            className="btn btn-error"
            disabled={!generatedSnippet}
          >
            Reset
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
    </ModalParent>
  );
}
