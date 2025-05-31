import { create } from "zustand";
import { SearchType } from "../model/projectCategory";

type ProjectSelectionStore = {
    selectionPlatform: string;
    selectionProject: string;
    searchType: SearchType;
    setSelectionPlatform: (platform: string) => void;
    setSelectionProject: (project: string) => void;
    setSearchType: (searchType: SearchType) => void;
}

const useProjectSelectionStore = create<ProjectSelectionStore>((set) => ({
    selectionPlatform: "",
    selectionProject: "",
    searchType: SearchType.LOCAL,
    setSelectionPlatform: (platform: string) => set(() => {
        return { selectionPlatform: platform, selectionProject: "", searchType: SearchType.LOCAL }
    }),
    setSelectionProject: (project: string) => set(() => { return { selectionProject: project, searchType: SearchType.LOCAL } }),
    setSearchType: (searchType: SearchType) => set(() => { return { searchType: searchType } })
}))

export default useProjectSelectionStore;

