import { FaLightbulb, FaSpinner } from "react-icons/fa";
import { useShallow } from "zustand/shallow";
import useChatStore from "../../context/chatStore";
import RenderProjectList from "./RenderProjectList";

export default function ProjectList() {
  const { projects, jwt } = useChatStore(
    useShallow((state) => ({
      projects: state.projects,
      jwt: state.jwt,
    }))
  );

  const isLoading = jwt && !projects;

  return (
    <div className="bg-gray-800 rounded-lg shadow-lg">
      <div className="p-4">
        {isLoading ? (
          <div className="text-center text-gray-400">
            <FaSpinner className="text-4xl mx-auto mb-4 text-gray-600 animate-spin" />
            <p>Loading projects...</p>
          </div>
        ) : (
          <>

            <RenderProjectList
              title="LightRAG Projects"
              projectList={projects?.lightrag_projects?.projects || []}
              colorScheme="green"
              platform="lightrag"
            />

            <RenderProjectList
              title="CAG Projects"
              projectList={projects?.cag_projects?.projects || []}
              colorScheme="yellow"
              platform="cag"
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
          </>
        )}
      </div>
    </div>
  );
}
