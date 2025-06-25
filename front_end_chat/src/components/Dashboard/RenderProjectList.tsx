import { useState } from "react";
import { FaLightbulb } from "react-icons/fa";
import { useDashboardStore } from "../../context/dashboardStore";
import { ApiProject } from "../../types/types";
import ChatConfigDialog from "../ChatConfigDialog";
import { Platform } from "../../model/projectCategory";

type RenderProjectListProps = {
  title: string;
  projectList: ApiProject[];
  colorScheme: "blue" | "green";
  selectedProjects: string[];
};

const colors = {
  blue: {
    title: "text-blue-300",
    selected: "bg-blue-900 border-blue-500",
    icon: "bg-blue-500",
    iconSelected: "text-blue-900",
    name: "text-blue-400",
    nameSelected: "text-white",
  },
  green: {
    title: "text-green-300",
    selected: "bg-green-900 border-green-500",
    icon: "bg-green-500",
    iconSelected: "text-green-900",
    name: "text-green-400",
    nameSelected: "text-white",
  },
};

export default function RenderProjectList({
  title,
  projectList,
  colorScheme,
  selectedProjects,
}: RenderProjectListProps) {
  const { toggleProjectSelection } = useDashboardStore();
  const [showDialog, setShowDialog] = useState(false);

  if (!projectList || projectList.length === 0) return null;

  const scheme = colors[colorScheme];

  return (
    <div className="mb-8">
      <h2 className={`text-xl font-bold ${scheme.title} mb-4`}>{title}</h2>
      <div className="space-y-2">
        {projectList.map((project: ApiProject, index: number) => {
          const uniqueId = `${colorScheme}_${project.name}_${index}`;
          const isSelected = selectedProjects.includes(uniqueId);

          return (
            <div
              key={uniqueId}
              className={`flex justify-between items-center p-4 rounded-lg cursor-pointer hover:bg-gray-700 transition-colors duration-200 border-b border-gray-700 last:border-b-0 ${
                isSelected ? scheme.selected : "border-transparent"
              }`}
              onClick={() => toggleProjectSelection(uniqueId)}
            >
              <div className="flex items-center">
                <div
                  className={`p-3 rounded-full mr-4 ${
                    isSelected ? "bg-white" : scheme.icon
                  }`}
                >
                  <FaLightbulb
                    className={isSelected ? scheme.iconSelected : "text-white"}
                  />
                </div>
                <div>
                  <h3
                    className={`text-lg font-semibold ${
                      isSelected ? scheme.nameSelected : scheme.name
                    }`}
                  >
                    {project.name}
                  </h3>

                  <p className="text-xs text-gray-500">
                    Files: {project.input_files?.length || 0}
                  </p>
                </div>
              </div>

              {/* Button to chat */}
              <button
                onClick={() => {
                  setShowDialog(true);
                }}
                // disabled={!selectionProject}
                className="bg-blue-500  px-4 py-2 rounded-md"
              >
                <a href={`#`} className="!text-white">
                  Start Chat
                </a>
              </button>
              {showDialog && (
                <ChatConfigDialog
                  isOpen={showDialog}
                  onClose={() => setShowDialog(false)}
                  project={project}
                  platform={
                    colorScheme === "blue"
                      ? ("graphrag" as Platform)
                      : ("lightrag" as Platform)
                  }
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
