import CenteredLayout from "./CenteredLayout";
import useChatStore from "../context/chatStore";
import { useShallow } from "zustand/react/shallow";
import { Platform } from "../model/projectCategory";
import { useState } from "react";

export default function ProjectSelector() {
    const [selectionPlatform, setSelectionPlatform] = useState("");
    const [selectionProject, setSelectionProject] = useState("");
    const { projects } = useChatStore(useShallow((state) => ({
        projects: state.projects
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
                <select className="select select-primary w-full" 
                value={selectionPlatform}
                onChange={(e) => setSelectionPlatform(e.target.value)}>
                    <option disabled>Pick a platform</option>
                    <option value="">--</option>
                    {Object.values(Platform).map((platform, index) => (
                        <option key={`${index}-${platform}`} value={platform}>{platform}</option>
                    ))}
                </select>
                {selectionPlatform && (
                    <div className="w-full">
                        <h3 className="text-lg py-2">Select a project</h3>
                        <select className="select select-primary w-full" value={selectionProject} 
                        onChange={(e) => setSelectionProject(e.target.value)}>
                            <option value="">--</option>
                            <option disabled>Pick a project</option>
                            {getProjects().map(p => (
                                <option value={p.name}>{p.name}</option>
                            ))}
                        </select>
                    </div>
                )}
            </div>
        </CenteredLayout>
    )
}
