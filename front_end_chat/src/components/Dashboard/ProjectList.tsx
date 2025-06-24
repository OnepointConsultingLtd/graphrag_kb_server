import { useEffect, useState } from "react";
import { FaLightbulb } from "react-icons/fa";
import { useDashboardStore } from "../../context/dashboardStore";
import { ApiProjectsResponse } from "../../types/types";
import RenderProjectList from "../Dashboard/RenderProjectList";
import Loading from "../Loading";

export default function ProjectList() {
  const { projects, selectedProjects, setProjects } = useDashboardStore();
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      const token = localStorage.getItem("authToken");
      const isTokenValidated =
        localStorage.getItem("tokenValidated") === "true";

      if (!token || !isTokenValidated) {
        setError("No valid token found. Please login again.");
        setIsLoading(false);
        return;
      }

      const response = await fetch(`http://localhost:9999/protected/projects`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setProjects(data);
      setError(null);
    } catch (error) {
      console.error("Error fetching projects:", error);
      setError("Failed to load projects. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return <Loading />;
  }

  if (error) {
    return (
      <div className="bg-gray-800 rounded-lg shadow-lg p-6">
        <div className="text-center">
          <p className="text-red-400 mb-4">{error}</p>
          <button
            onClick={fetchProjects}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors duration-200"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Check if projects is the API response structure
  const apiProjects = projects as ApiProjectsResponse;

  return (
    <div className="bg-gray-800 rounded-lg shadow-lg">
      <div className="p-4">
        <RenderProjectList
          title="GraphRAG Projects"
          projectList={apiProjects.graphrag_projects?.projects || []}
          colorScheme="blue"
          selectedProjects={selectedProjects}
        />

        <RenderProjectList
          title="LightRAG Projects"
          projectList={apiProjects.lightrag_projects?.projects || []}
          colorScheme="green"
          selectedProjects={selectedProjects}
        />

        {/* Show message if no projects found */}
        {(!apiProjects.graphrag_projects?.projects ||
          apiProjects.graphrag_projects.projects.length === 0) &&
          (!apiProjects.lightrag_projects?.projects ||
            apiProjects.lightrag_projects.projects.length === 0) && (
            <div className="text-center text-gray-400">
              <FaLightbulb className="text-4xl mx-auto mb-4 text-gray-600" />
              <p>No projects found</p>
            </div>
          )}
      </div>
    </div>
  );
}
