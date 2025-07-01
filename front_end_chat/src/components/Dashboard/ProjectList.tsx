import { FaLightbulb } from "react-icons/fa";
import { useShallow } from "zustand/shallow";
import useChatStore from "../../context/chatStore";
import RenderProjectList from "../dashboard/RenderProjectList";

export default function ProjectList() {
  const { projects } = useChatStore(
    useShallow((state) => ({
      projects: state.projects,
    })),
  );

  return (
    <div className="bg-gray-800 rounded-lg shadow-lg">
      <div className="p-4">
        <RenderProjectList
          title="GraphRAG Projects"
          projectList={projects?.graphrag_projects?.projects || []}
          colorScheme="blue"
          platform="graphrag"
        />

        <RenderProjectList
          title="LightRAG Projects"
          projectList={projects?.lightrag_projects?.projects || []}
          colorScheme="green"
          platform="lightrag"
        />

        {/* Show message if no projects found */}
        {(!projects?.graphrag_projects?.projects ||
          projects?.graphrag_projects?.projects.length === 0) &&
          (!projects?.lightrag_projects?.projects ||
            projects?.lightrag_projects?.projects.length === 0) && (
            <div className="text-center text-gray-400">
              <FaLightbulb className="text-4xl mx-auto mb-4 text-gray-600" />
              <p>No projects found</p>
            </div>
          )}
      </div>
    </div>
  );
}
