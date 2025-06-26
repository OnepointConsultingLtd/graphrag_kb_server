import { create } from "zustand";
import { SearchType } from "../model/projectCategory";

type ProjectSelectionStore = {
    selectionPlatform: string;
    selectionProject: string;
    additionalPromptInstructions: string,
    searchType: SearchType;
    setSelectionPlatform: (platform: string) => void;
    setSelectionProject: (project: string) => void;
    setSearchType: (searchType: SearchType) => void;
    setAdditionalPromptInstructions: (additionalPromptInstructions: string) => void;
    setSelectionProjectAndPlatform: (project: string, platform: string) => void;
    isChatConfigDialogOpen: boolean;
    setIsChatConfigDialogOpen: (isOpen: boolean) => void;
}

const useProjectSelectionStore = create<ProjectSelectionStore>((set) => ({
    selectionPlatform: "",
    selectionProject: "",
    searchType: SearchType.LOCAL,
    additionalPromptInstructions: "",
    isChatConfigDialogOpen: false,
    setSelectionPlatform: (platform: string) => set(() => {
        return { selectionPlatform: platform, selectionProject: "", searchType: SearchType.LOCAL }
    }),
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
    setIsChatConfigDialogOpen: (isChatConfigDialogOpen: boolean) => set(() => { return { isChatConfigDialogOpen } })
    
}))

export default useProjectSelectionStore;

