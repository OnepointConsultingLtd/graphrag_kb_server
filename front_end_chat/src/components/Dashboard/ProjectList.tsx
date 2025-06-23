import { FaLightbulb } from "react-icons/fa";
import { useDashboardStore } from "../../context/dashboardStore";

export default function ProjectList() {
  const { projects, selectedProjects, toggleProjectSelection } =
    useDashboardStore();

  return (
    <div className="bg-gray-800 rounded-lg shadow-lg">
      <div className="space-y-2 p-4">
        {projects.map((project) => {
          const isSelected = selectedProjects.includes(project.id);
          return (
            <div
              key={project.id}
              className={`flex items-center p-4 rounded-lg cursor-pointer hover:bg-gray-700 transition-colors duration-200 border-b border-gray-700 last:border-b-0 ${
                isSelected
                  ? "bg-blue-900 border-blue-500"
                  : "border-transparent"
              }`}
              onClick={() => toggleProjectSelection(project.id)}
            >
              <div
                className={`p-3 rounded-full mr-4 ${
                  isSelected ? "bg-white" : "bg-blue-500"
                }`}
              >
                <FaLightbulb
                  className={isSelected ? "text-blue-900" : "text-white"}
                />
              </div>
              <div>
                <h3
                  className={`text-lg font-semibold ${
                    isSelected ? "text-white" : "text-blue-400"
                  }`}
                >
                  {project.name}
                </h3>
                <p className="text-sm text-gray-400">{project.engine}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
