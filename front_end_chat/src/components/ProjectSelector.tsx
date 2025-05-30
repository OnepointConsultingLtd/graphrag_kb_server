import CenteredLayout from "./CenteredLayout";
import useChatStore from "../context/chatStore";
import { useShallow } from "zustand/react/shallow";
import { Platform } from "../model/projectCategory";
import { useState } from "react";

function SelectPlatform({ selectionPlatform, setSelectionPlatform, setSelectionProject }: 
    { selectionPlatform: string, 
        setSelectionPlatform: (project: () => void) => void, 
        setSelectionProject: (project: string) => void }) {
    return <select className="select select-primary w-full"
        value={selectionPlatform}
        onChange={(e) => setSelectionPlatform(() => {
            setSelectionProject("");
            return e.target.value
        })}>
        <option disabled>Pick a platform</option>
        <option value="">--</option>
        {Object.values(Platform).map((platform, index) => (
            <option key={`${index}-${platform}`} value={platform}>{platform}</option>
        ))}
    </select>
}

export default function ProjectSelector() {
    const [selectionPlatform, setSelectionPlatform] = useState("");
    const [selectionProject, setSelectionProject] = useState("");
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
                <SelectPlatform 
                    selectionPlatform={selectionPlatform} 
                    setSelectionPlatform={setSelectionPlatform} 
                    setSelectionProject={setSelectionProject} />
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
                        <div className="w-full flex justify-end mt-6">
                            <button className="btn btn-primary w-[200px]" type="button"
                                onClick={() => {
                                    setSelectedProject({
                                        name: selectionProject,
                                        updated_timestamp: new Date(),
                                        input_files: []
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
