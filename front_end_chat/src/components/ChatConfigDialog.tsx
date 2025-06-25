import { useState } from "react";
import { ApiProject } from "../types/types";
import { Platform, SearchType } from "../model/projectCategory";
import RenderLabel from "./Dashboard/Form/RenderLabel";
import useChatStore from "../context/chatStore";
import useProjectSelectionStore from "../context/projectSelectionStore";
import { useShallow } from "zustand/shallow";

interface ChatConfigDialogProps {
  isOpen: boolean;
  onClose: () => void;
  project: ApiProject;
  platform: Platform;
}

// TODO: Talk to Gil.
const ChatTypeSelector = ({
  isFloating,
  setIsFloating,
}: {
  isFloating: boolean;
  setIsFloating: (value: boolean) => void;
}) => (
  <div className="mb-6">
    <label className="block text-sm font-medium text-gray-300 mb-2">
      Chat Type
    </label>
    <div className="space-y-2">
      <label className="flex items-center">
        <input
          type="radio"
          name="chatType"
          checked={!isFloating}
          onChange={() => setIsFloating(false)}
          className="mr-2 text-blue-600"
        />
        <span className="text-gray-300">Full Page Chat</span>
      </label>
      <label className="flex items-center">
        <input
          type="radio"
          name="chatType"
          checked={isFloating}
          onChange={() => setIsFloating(true)}
          className="mr-2 text-blue-600"
        />
        <span className="text-gray-300">Floating Chat</span>
      </label>
    </div>
  </div>
);

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
  <div>
    <RenderLabel label="Additional Instructions" />
    <textarea
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="textarea textarea-bordered w-full bg-gray-700"
      placeholder="Enter any additional instructions for the chat..."
    />
  </div>
);

const ActionButtons = ({
  onCancel,
  onStartChat,
}: {
  onCancel: () => void;
  onStartChat: () => void;
}) => (
  <div className="flex space-x-3 mt-6">
    <button
      onClick={onCancel}
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

export default function ChatConfigDialog({
  isOpen,
  onClose,
  project,
  platform,
}: ChatConfigDialogProps) {
  const [isFloating, setIsFloating] = useState(false);
  const { setSelectedProject } = useChatStore();
  const {
    additionalPromptInstructions,
    setAdditionalPromptInstructions,
    searchType,
    setSearchType,
  } = useProjectSelectionStore(
    useShallow((state) => ({
      additionalPromptInstructions: state.additionalPromptInstructions,
      setAdditionalPromptInstructions: state.setAdditionalPromptInstructions,
      searchType: state.searchType,
      setSearchType: state.setSearchType,
    }))
  );

  const handleStartChat = () => {
    setSelectedProject({
      id: project.id,
      name: project.name,
      updated_timestamp: project.updated_timestamp,
      input_files: (project.input_files ?? []) as string[],
      search_type: searchType,
      platform: platform,
      additional_prompt_instructions: additionalPromptInstructions,
    });

    const targetPath = isFloating ? "/floating-chat" : "/";
    window.location.href = targetPath;
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-gray-800 rounded-lg p-6 w-full max-w-md mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-xl font-bold text-white mb-4">
          Configure Chat for {project.name}
        </h2>

        <ChatTypeSelector
          isFloating={isFloating}
          setIsFloating={setIsFloating}
        />

        <SearchTypeSelector
          searchType={searchType}
          setSearchType={setSearchType}
        />

        <AdditionalInstructionsInput
          value={additionalPromptInstructions}
          onChange={setAdditionalPromptInstructions}
        />

        <ActionButtons onCancel={onClose} onStartChat={handleStartChat} />
      </div>
    </div>
  );
}
