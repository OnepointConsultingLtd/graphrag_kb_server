import { useShallow } from "zustand/shallow";
import useChatStore from "../context/chatStore";
import useProjectSelectionStore from "../context/projectSelectionStore";
import { ChatType } from "../lib/chatTypes";
import { Platform, SearchType } from "../model/projectCategory";
import { ChatTypeOptions } from "../types/types";
import RenderLabel from "./Dashboard/Form/RenderLabel";

// TODO: Talk to Gil.
const ChatTypeSelector = () => {
  const { chatType, setChatType } = useChatStore(
    useShallow((state) => ({
      chatType: state.chatType,
      setChatType: state.setChatType,
    }))
  );

  const { selectionProject, selectionPlatform } = useProjectSelectionStore(
    useShallow((state) => ({
      selectionProject: state.selectionProject,
      selectionPlatform: state.selectionPlatform,
    }))
  );

  return (
    <div className="mb-6">
      <h3 className="block text-sm font-medium text-gray-300 mb-2">
        Chat Type
      </h3>
      <div className="space-y-2">
        {Object.entries(ChatType).map(([key, value]) => (
          <label
            className="flex items-center"
            key={`${key}-${selectionProject}-${selectionPlatform}`}
          >
            <input
              type="radio"
              checked={chatType === value}
              onChange={() => setChatType(value as ChatTypeOptions)}
              className="mr-2 text-blue-600"
              value={value}
            />

            <span className="text-gray-300">{key}</span>
          </label>
        ))}
      </div>
    </div>
  );
};

const SearchTypeSelector = ({
  searchType,
  setSearchType,
}: {
  searchType: SearchType;
  setSearchType: (value: SearchType) => void;
}) => (
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

const AdditionalInstructionsInput = ({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) => (
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

const ActionButtons = ({ onStartChat }: { onStartChat: () => void }) => {
  const { setIsChatConfigDialogOpen } = useProjectSelectionStore(
    useShallow((state) => ({
      setIsChatConfigDialogOpen: state.setIsChatConfigDialogOpen,
    }))
  );

  return (
    <div className="flex space-x-3 mt-6">
      <button
        onClick={() => setIsChatConfigDialogOpen(false)}
        className="flex-1 cursor-pointer bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-md transition-colors duration-200"
      >
        Cancel
      </button>
      <button
        onClick={onStartChat}
        className="flex-1 cursor-pointer bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md transition-colors duration-200"
      >
        Start Chat
      </button>
    </div>
  );
};

export default function ChatConfigDialog() {
  const { setSelectedProject, chatType } = useChatStore(
    useShallow((state) => ({
      setSelectedProject: state.setSelectedProject,
      chatType: state.chatType,
    }))
  );

  const {
    additionalPromptInstructions,
    setAdditionalPromptInstructions,
    searchType,
    setSearchType,
    selectionProject,
    selectionPlatform,
  } = useProjectSelectionStore(
    useShallow((state) => ({
      additionalPromptInstructions: state.additionalPromptInstructions,
      setAdditionalPromptInstructions: state.setAdditionalPromptInstructions,
      searchType: state.searchType,
      setSearchType: state.setSearchType,
      selectionProject: state.selectionProject,
      selectionPlatform: state.selectionPlatform,
    }))
  );

  console.log("selectionProject", selectionProject);
  const handleStartChat = () => {
    setSelectedProject({
      name: selectionProject,
      updated_timestamp: new Date(),
      input_files: [],
      search_type: searchType,
      platform: selectionPlatform as Platform,
      additional_prompt_instructions: additionalPromptInstructions,
    });

    const targetPath = chatType === ChatType.FLOATING ? "/floating-chat" : "/";
    window.location.href = targetPath;
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div
        className="bg-gray-800 rounded-lg p-6 w-full max-w-md mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-xl font-bold text-white mb-4">
          Configure Chat for {selectionProject}
        </h2>

        <ChatTypeSelector />

        <SearchTypeSelector
          searchType={searchType}
          setSearchType={setSearchType}
        />

        <AdditionalInstructionsInput
          value={additionalPromptInstructions}
          onChange={setAdditionalPromptInstructions}
        />

        <ActionButtons onStartChat={handleStartChat} />
      </div>
    </div>
  );
}
