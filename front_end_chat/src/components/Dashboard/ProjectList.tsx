import { FaLightbulb } from "react-icons/fa";
import { useShallow } from "zustand/shallow";
import useChatStore from "../../context/chatStore";
import { useDashboardStore } from "../../context/dashboardStore";
import RenderProjectList from "../Dashboard/RenderProjectList";

export default function ProjectList() {
  const { selectedProjects } = useDashboardStore();

  const { projects } = useChatStore(
    useShallow((state) => ({
      projects: state.projects,
    }))
  );

  const apiProjects = projects;

  return (
    <div className="bg-gray-800 rounded-lg shadow-lg">
      <div className="p-4">
        <RenderProjectList
          title="GraphRAG Projects"
          projectList={apiProjects?.graphrag_projects?.projects || []}
          colorScheme="blue"
          selectedProjects={selectedProjects}
        />

        <RenderProjectList
          title="LightRAG Projects"
          projectList={apiProjects?.lightrag_projects?.projects || []}
          colorScheme="green"
          selectedProjects={selectedProjects}
        />

        {/* Show message if no projects found */}
        {(!apiProjects?.graphrag_projects?.projects ||
          apiProjects?.graphrag_projects?.projects.length === 0) &&
          (!apiProjects?.lightrag_projects?.projects ||
            apiProjects?.lightrag_projects?.projects.length === 0) && (
            <div className="text-center text-gray-400">
              <FaLightbulb className="text-4xl mx-auto mb-4 text-gray-600" />
              <p>No projects found</p>
            </div>
          )}
      </div>
    </div>
  );
}
