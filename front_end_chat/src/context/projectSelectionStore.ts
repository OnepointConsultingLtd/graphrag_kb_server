import { create } from "zustand";
import { SearchType, SimpleProject } from "../model/projectCategory";
import { ChatTypeOptions } from "../types/types";

type ProjectSelectionStore = {
    selectionPlatform: string;
    selectionProject: string;
    additionalPromptInstructions: string,
    searchType: SearchType;
    isChatConfigDialogOpen: boolean;
    localChatType: ChatTypeOptions;
    setSelectionProject: (project: string) => void;
    setSearchType: (searchType: SearchType) => void;
    setAdditionalPromptInstructions: (additionalPromptInstructions: string) => void;
    setSelectionProjectAndPlatform: (project: string, platform: string) => void;
    setIsChatConfigDialogOpen: (isOpen: boolean, project: SimpleProject | null) => void;
    setLocalChatType: (localChatType: ChatTypeOptions) => void;
    logout: () => void;
}

const useProjectSelectionStore = create<ProjectSelectionStore>((set) => ({
    selectionPlatform: "",
    selectionProject: "",
    searchType: SearchType.LOCAL,
    additionalPromptInstructions: "",
    isChatConfigDialogOpen: false,
    localChatType: null,
    setSelectionProject: (project: string) => set(() => { return { selectionProject: project, searchType: SearchType.LOCAL } }),
    setSearchType: (searchType: SearchType) => set(() => { return { searchType: searchType } }),
    setAdditionalPromptInstructions: (additionalPromptInstructions: string) =>
        set(() => { return { additionalPromptInstructions: additionalPromptInstructions } }),

    setSelectionProjectAndPlatform: (selectionProject: string, selectionPlatform: string) => set((state) => {
        if (state.selectionPlatform === selectionPlatform && state.selectionProject === selectionProject) {
            return {
                selectionPlatform: "",
                selectionProject: "",
                searchType: SearchType.LOCAL
            }
        }

        return { selectionProject, selectionPlatform, searchType: SearchType.LOCAL }
    }),
    setIsChatConfigDialogOpen: (isChatConfigDialogOpen: boolean, project: SimpleProject | null) =>
        set(() => {
            if (!project) {
                return { isChatConfigDialogOpen, selectionPlatform: "", selectionProject: "" }
            }
            return { isChatConfigDialogOpen, selectionPlatform: project.platform, selectionProject: project.name }
        }),
    setLocalChatType: (localChatType: ChatTypeOptions) => set(() => ({ localChatType })),
    logout: () => set(() => ({ 
        selectionPlatform: "", 
        selectionProject: "", 
        searchType: SearchType.LOCAL, 
        additionalPromptInstructions: "", 
        isChatConfigDialogOpen: false,
        localChatType: null 
    }))
}))

export default useProjectSelectionStore;

