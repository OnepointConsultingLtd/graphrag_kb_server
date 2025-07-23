import ModalParent from "./ModalParent";
import FieldAdditionalInstructions from "./Form/FieldAdditionalInstructions";
import FieldEmail from "./Form/FieldEmail";
import FieldSearchType from "./Form/FieldSearchType";
import FieldWidgetType from "./Form/FieldWidgetType";
import RenderProjectPlatform from "./Form/RenderProjectPlatform";
import ModalTitle from "./ModalTitle";
import { useDashboardStore } from "../../context/dashboardStore";
import { useShallow } from "zustand/react/shallow";
import useProjectSelectionStore from "../../context/projectSelectionStore";
import useChatStore from "../../context/chatStore";
import { generateDirectUrl } from "../../lib/apiClient";
import { Platform } from "../../model/projectCategory";
import CopyToClipboard from "../buttons/CopyToClipboard";
import { StreamingSelector } from "./StreamingSelector";
export const GENERATE_URL_MODAL_ID = "generate-url-modal";

export default function GenerateURLModal() {
  const { useStreaming } = useChatStore(
    useShallow((state) => ({
      useStreaming: state.useStreaming,
    })),
  );
  const {
    email,
    widgetType,
    isGenerateUrlSubmitting,
    generateUrl,
    generateUrlError,
    setIsGenerateUrlSubmitting,
    setGenerateUrlDialogOpen,
    setGenerateUrl,
    setGenerateUrlError,
  } = useDashboardStore(
    useShallow((state) => ({
      email: state.email,
      widgetType: state.widgetType,
      isGenerateUrlSubmitting: state.isGenerateUrlSubmitting,
      generateUrl: state.generateUrl,
      generateUrlError: state.generateUrlError,
      setGenerateUrlDialogOpen: state.setGenerateUrlDialogOpen,
      setIsGenerateUrlSubmitting: state.setIsGenerateUrlSubmitting,
      setGenerateUrl: state.setGenerateUrl,
      setGenerateUrlError: state.setGenerateUrlError,
    })),
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
    })),
  );

  const { jwt } = useChatStore(
    useShallow((state) => ({
      jwt: state.jwt,
    })),
  );

  function handleClose() {
    setGenerateUrlDialogOpen(false);
    handleReset();
  }

  function handleReset() {
    setGenerateUrl(null);
    setGenerateUrlError(null);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setIsGenerateUrlSubmitting(true);
    generateDirectUrl(jwt, {
      email: email,
      chat_type: widgetType,
      project: {
        name: selectionProject,
        search_type: searchType,
        platform: selectionPlatform as Platform,
        additional_prompt_instructions: additionalPromptInstructions,
        updated_timestamp: new Date(),
        input_files: [],
      },
      streaming: String(useStreaming),
    })
      .then((response) => {
        setGenerateUrl(response.url);
      })
      .catch((error) => {
        setGenerateUrlError(error.message);
      })
      .finally(() => {
        setIsGenerateUrlSubmitting(false);
      });
  }

  function handleCopyToClipboard() {
    if (generateUrl) {
      navigator.clipboard.writeText(generateUrl);
    }
  }

  return (
    <ModalParent id={GENERATE_URL_MODAL_ID}>
      <div>
        <ModalTitle title="Generate URL" />
        <form onSubmit={handleSubmit}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FieldEmail />
            <FieldWidgetType />
          </div>
          <div className="grid grid-cols-1 gap-2 mt-4">
            <FieldSearchType />
            <RenderProjectPlatform />
            <StreamingSelector />
            <FieldAdditionalInstructions />
          </div>
          {isGenerateUrlSubmitting && <div>Loading ...</div>}
          {generateUrlError && (
            <div className="alert alert-error mt-4">{generateUrlError}</div>
          )}
          {generateUrl && (
            <div className="alert alert-success mt-4 overflow-hidden whitespace-nowrap text-ellipsis flex justify-between">
              <a
                href={generateUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-white"
              >
                Link to chat
              </a>
              <CopyToClipboard handleCopyToClipboard={handleCopyToClipboard} />
            </div>
          )}
          {generateUrl && (
            <textarea
              value={generateUrl}
              className="textarea textarea-primary w-full bg-gray-700 mt-4 h-36"
            />
          )}
          <div className="modal-action mt-6">
            <button
              type="button"
              onClick={handleClose}
              className="btn btn-ghost"
              disabled={isGenerateUrlSubmitting}
            >
              Close
            </button>
            <button
              type="button"
              onClick={() => handleReset()}
              className="btn btn-error"
              disabled={isGenerateUrlSubmitting || !generateUrl}
            >
              Reset
            </button>
            <button
              type="submit"
              className="btn btn-secondary"
              disabled={isGenerateUrlSubmitting || !selectionProject}
            >
              {isGenerateUrlSubmitting ? (
                <span className="loading loading-spinner"></span>
              ) : (
                "Generate"
              )}
            </button>
          </div>
        </form>
      </div>
    </ModalParent>
  );
}
