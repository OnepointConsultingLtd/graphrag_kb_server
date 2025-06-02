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
}

const useProjectSelectionStore = create<ProjectSelectionStore>((set) => ({
    selectionPlatform: "",
    selectionProject: "",
    searchType: SearchType.LOCAL,
    additionalPromptInstructions: "",
    setSelectionPlatform: (platform: string) => set(() => {
        return { selectionPlatform: platform, selectionProject: "", searchType: SearchType.LOCAL }
    }),
    setSelectionProject: (project: string) => set(() => { return { selectionProject: project, searchType: SearchType.LOCAL } }),
    setSearchType: (searchType: SearchType) => set(() => { return { searchType: searchType } }),
    setAdditionalPromptInstructions: (additionalPromptInstructions: string) => 
        set(() => { return { additionalPromptInstructions: additionalPromptInstructions } })
}))

export default useProjectSelectionStore;

