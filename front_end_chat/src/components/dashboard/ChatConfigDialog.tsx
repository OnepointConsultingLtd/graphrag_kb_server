import { useNavigate } from "react-router-dom";
import { useShallow } from "zustand/shallow";
import useChatStore from "../../context/chatStore";
import useProjectSelectionStore from "../../context/projectSelectionStore";
import { ChatType } from "../../lib/chatTypes";
import { supportsStreaming } from "../../lib/streamingUtils";
import { Platform, SearchType } from "../../model/projectCategory";
import { ChatTypeOptions } from "../../model/types";
import RenderLabel from "./Form/RenderLabel";
import ModalParent from "./ModalParent";
import ModalTitle from "./ModalTitle";
import { StreamingSelector } from "./StreamingSelector";

function ChatTypeSelector() {
  const {
    selectionProject,
    selectionPlatform,
    localChatType,
    setLocalChatType,
  } = useProjectSelectionStore(
    useShallow((state) => ({
      selectionProject: state.selectionProject,
      selectionPlatform: state.selectionPlatform,
      localChatType: state.localChatType,
      setLocalChatType: state.setLocalChatType,
    })),
  );

  return (
    <div className="mb-6">
      <h3 className="block text-sm font-medium text-gray-300 mb-2">
        Chat Type
      </h3>
      <div className="space-y-2">
        {Object.entries(ChatType).map(([key, value]) => {
          const isChecked = localChatType === value;
          return (
            <label
              className="flex items-center"
              key={`${key}-${selectionProject}-${selectionPlatform}`}
            >
              <input
                type="radio"
                checked={isChecked}
                onChange={() => setLocalChatType(value as ChatTypeOptions)}
                className="mr-2 text-blue-600"
                value={value}
              />

              <span className="text-gray-300">{key}</span>
            </label>
          );
        })}
      </div>
    </div>
  );
}

function SearchTypeSelector({
  searchType,
  setSearchType,
}: {
  searchType: SearchType;
  setSearchType: (value: SearchType) => void;
}) {
  return (
    <div className="mb-6">
      <label className="block text-sm font-medium text-gray-300 mb-2">
        Search Type
      </label>
      <select
        className="select select-primary w-full"
        value={searchType}
        onChange={(e) => setSearchType(e.target.value as SearchType)}
      >
        {Object.values(SearchType).map((value, index) => (
          <option key={`${index}-${value}`} value={value}>
            {value}
          </option>
        ))}
      </select>
    </div>
  );
}

function AdditionalInstructionsInput({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="flex flex-col gap-1 cursor-auto">
      <RenderLabel label="Additional Instructions" />
      <span className="text-sm text-gray-400 mb-2">
        Example: "Please talk like Mark Zuckerberg."
      </span>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="textarea textarea-bordered w-full bg-gray-700"
        placeholder="Enter any additional instructions for the chat..."
      />
    </div>
  );
}

function ActionButtons({ onStartChat }: { onStartChat: () => void }) {
  const { setIsChatConfigDialogOpen, localChatType } = useProjectSelectionStore(
    useShallow((state) => ({
      setIsChatConfigDialogOpen: state.setIsChatConfigDialogOpen,
      localChatType: state.localChatType,
    })),
  );

  return (
    <div className="flex space-x-3 mt-6">
      <button
        onClick={() => setIsChatConfigDialogOpen(false, null)}
        className="flex-1 cursor-pointer bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-md transition-colors duration-200"
      >
        Cancel
      </button>
      <button
        onClick={onStartChat}
        className="flex-1 cursor-pointer bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
        disabled={!localChatType}
      >
        Start Chat
      </button>
    </div>
  );
}

export const CHAT_CONFIG_DIALOG_ID = "chat-config-dialog";

export default function ChatConfigDialog() {
  const navigate = useNavigate();

  const { selectedProject, setSelectedProjectAndChatType } = useChatStore(
    useShallow((state) => ({
      selectedProject: state.selectedProject,
      setSelectedProjectAndChatType: state.setSelectedProjectAndChatType,
    })),
  );

  const {
    additionalPromptInstructions,
    setAdditionalPromptInstructions,
    searchType,
    setSearchType,
    selectionProject,
    localChatType,
  } = useProjectSelectionStore(
    useShallow((state) => ({
      additionalPromptInstructions: state.additionalPromptInstructions,
      setAdditionalPromptInstructions: state.setAdditionalPromptInstructions,
      searchType: state.searchType,
      setSearchType: state.setSearchType,
      selectionProject: state.selectionProject,
      localChatType: state.localChatType,
    })),
  );

  function handleStartChat() {
    setSelectedProjectAndChatType(
      {
        name: selectionProject,
        updated_timestamp: new Date(),
        input_files: [],
        search_type: searchType,
        platform: selectedProject?.platform as Platform,
        additional_prompt_instructions: additionalPromptInstructions,
      },
      localChatType,
    );

    const targetPath =
      localChatType === ChatType.FLOATING ? "/floating-chat" : "/chat";
    navigate(targetPath);
  }

  return (
    <ModalParent id={CHAT_CONFIG_DIALOG_ID}>
      <div onClick={(e) => e.stopPropagation()}>
        <ModalTitle title={`Configure Chat for ${selectionProject}`} />

        <ChatTypeSelector />

        {supportsStreaming(selectedProject?.platform) && <StreamingSelector />}

        {selectedProject?.platform !== Platform.CAG && (
          <SearchTypeSelector
            searchType={searchType}
            setSearchType={setSearchType}
          />
        )}

        <AdditionalInstructionsInput
          value={additionalPromptInstructions}
          onChange={setAdditionalPromptInstructions}
        />

        <ActionButtons onStartChat={handleStartChat} />
      </div>
    </ModalParent>
  );
}
