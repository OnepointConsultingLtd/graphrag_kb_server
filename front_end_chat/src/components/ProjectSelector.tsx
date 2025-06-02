import CenteredLayout from "./CenteredLayout";
import useChatStore from "../context/chatStore";
import { useShallow } from "zustand/react/shallow";
import { Platform, SearchType } from "../model/projectCategory";
import useProjectSelectionStore from "../context/projectSelectionStore";

function SelectPlatform() {
    const { selectionPlatform, setSelectionPlatform } = useProjectSelectionStore(useShallow((state) => ({
        selectionPlatform: state.selectionPlatform,
        setSelectionPlatform: state.setSelectionPlatform,
    })));
    return <select className="select select-primary w-full"
        value={selectionPlatform}
        onChange={(e) => setSelectionPlatform(e.target.value)}>
        <option disabled>Pick a platform</option>
        <option value="">--</option>
        {Object.values(Platform).map((platform, index) => (
            <option key={`${index}-${platform}`} value={platform}>{platform}</option>
        ))}
    </select>
}

function SelectSearchType() {
    const [searchType, setSearchType, selectionPlatform] = useProjectSelectionStore(useShallow((state) => [state.searchType, state.setSearchType, state.selectionPlatform]));
    return (
        <>
            <h3 className="text-lg py-2">Select search type</h3>
            <select className="select select-primary w-full" value={searchType}
                onChange={(e) => setSearchType(e.target.value as SearchType)}>
                {Object.values(SearchType)
                    .filter(value => !(selectionPlatform === Platform.LIGHTRAG && value === SearchType.DRIFT))
                    .map((value, index) => (
                        <option key={`${index}-${value}`} value={value}>{value}</option>
                    ))}
            </select>
        </>
    )
}

function AdditionalPromptInstructions() {
    const { selectionPlatform, additionalPromptInstructions, setAdditionalPromptInstructions } = useProjectSelectionStore(useShallow((state) => ({
        selectionPlatform: state.selectionPlatform,
        additionalPromptInstructions: state.additionalPromptInstructions,
        setAdditionalPromptInstructions: state.setAdditionalPromptInstructions
    })));
    if (selectionPlatform === Platform.GRAPHRAG) {
        return null;
    }
    return (
        <div className="w-full">
            <h3 className="text-lg py-2">Additional prompt instructions</h3>
            <textarea className="textarea textarea-primary w-full" placeholder="Additional prompt instructions" value={additionalPromptInstructions} 
                onChange={(e) => setAdditionalPromptInstructions(e.target.value)} />
        </div>
    )
}

export default function ProjectSelector() {
    const { selectionPlatform, selectionProject, setSelectionProject, searchType, additionalPromptInstructions } = useProjectSelectionStore(useShallow((state) => ({
        selectionPlatform: state.selectionPlatform,
        selectionProject: state.selectionProject,
        setSelectionProject: state.setSelectionProject,
        searchType: state.searchType,
        additionalPromptInstructions: state.additionalPromptInstructions
    })));
    const { projects, setSelectedProject } = useChatStore(useShallow((state) => ({
        projects: state.projects,
        setSelectedProject: state.setSelectedProject
    })));

    function getProjects() {
        if (selectionPlatform === Platform.GRAPHRAG) {
            return projects?.graphrag_projects.projects ?? [];
        }
        return projects?.lightrag_projects.projects ?? [];
    }

    return (
        <CenteredLayout title="Project Selector">
            <div className="w-full">
                <SelectPlatform />
                {selectionPlatform && (
                    <div className="w-full">
                        <h3 className="text-lg py-2">Select a project</h3>
                        <select className="select select-primary w-full" value={selectionProject}
                            onChange={(e) => setSelectionProject(e.target.value)}>
                            <option disabled>Pick a project</option>
                            <option value="">--</option>
                            {getProjects().map(p => (
                                <option value={p.name}>{p.name}</option>
                            ))}
                        </select>
                        <SelectSearchType />
                        <AdditionalPromptInstructions />
                        <div className="w-full flex justify-end mt-6">
                            <button className="btn btn-primary w-[200px]" type="button"
                                onClick={() => {
                                    setSelectedProject({
                                        name: selectionProject,
                                        updated_timestamp: new Date(),
                                        input_files: [],
                                        search_type: searchType,
                                        platform: selectionPlatform as Platform,
                                        additional_prompt_instructions: additionalPromptInstructions
                                    })
                                }}
                                disabled={!selectionProject}>Start Chat</button>
                        </div>
                    </div>
                )}
            </div>
        </CenteredLayout>
    )
}
