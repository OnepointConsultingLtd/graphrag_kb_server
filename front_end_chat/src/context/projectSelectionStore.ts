import { create } from "zustand";
import { SearchType, SimpleProject } from "../model/projectCategory";
import { ChatTypeOptions } from "../model/types";
import { CHAT_CONFIG_DIALOG_ID } from "../components/dashboard/ChatConfigDialog";
import { showCloseModal } from "../lib/dialog";

type ProjectSelectionStore = {
  selectionPlatform: string;
  selectionProject: string;
  additionalPromptInstructions: string;
  searchType: SearchType;
  isChatConfigDialogOpen: boolean;
  localChatType: ChatTypeOptions;
  setSelectionProject: (project: string) => void;
  setSearchType: (searchType: SearchType) => void;
  setAdditionalPromptInstructions: (
    additionalPromptInstructions: string,
  ) => void;
  setSelectionProjectAndPlatform: (
    project: string,
    platform: string,
    toggle: boolean,
  ) => void;
  setIsChatConfigDialogOpen: (
    isOpen: boolean,
    project: SimpleProject | null,
  ) => void;
  setLocalChatType: (localChatType: ChatTypeOptions) => void;
  logout: () => void;
};

function toggleChatConfigDialog(isOpen: boolean) {
  showCloseModal(isOpen, CHAT_CONFIG_DIALOG_ID);
}

const useProjectSelectionStore = create<ProjectSelectionStore>((set) => ({
  selectionPlatform: "",
  selectionProject: "",
  searchType: SearchType.LOCAL,
  additionalPromptInstructions: "",
  isChatConfigDialogOpen: false,
  localChatType: null,
  setSelectionProject: (project: string) =>
    set({ selectionProject: project, searchType: SearchType.LOCAL }),
  setSearchType: (searchType: SearchType) => set({ searchType: searchType }),
  setAdditionalPromptInstructions: (additionalPromptInstructions: string) =>
    set({ additionalPromptInstructions: additionalPromptInstructions }),

  setSelectionProjectAndPlatform: (
    selectionProject: string,
    selectionPlatform: string,
    toggle: boolean,
  ) =>
    set((state) => {
      if (
        state.selectionPlatform === selectionPlatform &&
        state.selectionProject === selectionProject &&
        toggle
      ) {
        return {
          selectionPlatform: "",
          selectionProject: "",
          searchType: SearchType.LOCAL,
        };
      }

      return {
        selectionProject,
        selectionPlatform,
        searchType: SearchType.LOCAL,
      };
    }),
  setIsChatConfigDialogOpen: (
    isChatConfigDialogOpen: boolean,
    project: SimpleProject | null,
  ) =>
    set(() => {
      toggleChatConfigDialog(isChatConfigDialogOpen);
      if (!project) {
        return {
          isChatConfigDialogOpen,
          selectionPlatform: "",
          selectionProject: "",
        };
      }
      return { isChatConfigDialogOpen, selectionProject: project.name };
    }),
  setLocalChatType: (localChatType: ChatTypeOptions) =>
    set(() => ({ localChatType })),
  logout: () =>
    set(() => ({
      selectionPlatform: "",
      selectionProject: "",
      searchType: SearchType.LOCAL,
      additionalPromptInstructions: "",
      isChatConfigDialogOpen: false,
      localChatType: null,
    })),
}));

export default useProjectSelectionStore;
