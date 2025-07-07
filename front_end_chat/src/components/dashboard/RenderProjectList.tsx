import { useEffect } from "react";
import { FaChevronDown, FaChevronUp, FaLightbulb } from "react-icons/fa";
import { useShallow } from "zustand/shallow";
import useChatStore from "../../context/chatStore";
import { useDashboardStore } from "../../context/dashboardStore";
import useProjectSelectionStore from "../../context/projectSelectionStore";
import { isProjectNotReady } from "../../lib/projectStatus";
import {
  Platform,
  SearchType,
  SimpleProject,
} from "../../model/projectCategory";

// Constants
const REFRESH_PROJECT_TIMEOUT = 1000 * 60 * 2; // 2 minutes in milliseconds

type RenderProjectListProps = {
  title: string;
  projectList: SimpleProject[];
  colorScheme: "blue" | "green" | "yellow";
  platform: string;
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
  yellow: {
    title: "text-yellow-300",
    selected: "bg-yellow-900 border-yellow-500",
    icon: "bg-yellow-500",
    iconSelected: "text-yellow-900",
    name: "text-yellow-400",
    nameSelected: "text-white",
  },
};

export default function RenderProjectList({
  title,
  projectList,
  colorScheme,
  platform,
}: RenderProjectListProps) {
  const {
    selectionProject,
    selectionPlatform,
    setSelectionProjectAndPlatform,
    setIsChatConfigDialogOpen,
  } = useProjectSelectionStore(
    useShallow((state) => ({
      selectionProject: state.selectionProject,
      selectionPlatform: state.selectionPlatform,
      setSelectionProjectAndPlatform: state.setSelectionProjectAndPlatform,
      setIsChatConfigDialogOpen: state.setIsChatConfigDialogOpen,
    }))
  );

  const { expandedSections, setExpandedSection } = useDashboardStore(
    useShallow((state) => ({
      expandedSections: state.expandedSections,
      setExpandedSection: state.setExpandedSection,
    }))
  );

  const { setSelectedProject, refreshProjects } = useChatStore(
    useShallow((state) => ({
      setSelectedProject: state.setSelectedProject,
      refreshProjects: state.refreshProjects,
    }))
  );

  useEffect(() => {
    const interval = setInterval(() => {
      refreshProjects();
    }, REFRESH_PROJECT_TIMEOUT);
    return () => clearInterval(interval);
  }, []);

  if (!projectList || projectList.length === 0) return null;

  const scheme = colors[colorScheme];
  const isExpanded = expandedSections[platform] ?? true; // Default to expanded

  const handleProjectClick = (project: SimpleProject, toggle: boolean) => {
    if (isProjectNotReady(project)) {
      return;
    }
    const isCurrentlySelected =
      selectionProject === project.name && selectionPlatform === platform;
    setSelectionProjectAndPlatform(project.name, platform, toggle);
    if (isCurrentlySelected && toggle) {
      setSelectedProject(undefined);
    } else {
      setSelectedProject({
        name: project.name,
        updated_timestamp: project.updated_timestamp,
        input_files: project.input_files,
        search_type: SearchType.LOCAL,
        platform: platform as Platform,
        additional_prompt_instructions: "",
      });
    }
  };

  console.log("isExpanded for", platform, isExpanded);
  return (
    <div className="mb-8">
      <div
        className="flex justify-between items-center cursor-pointer hover:border-b-2 hover:border-gray-700 pr-8"
        onClick={() => setExpandedSection(platform, !isExpanded)}
      >
        <h2
          className={`text-xl font-bold ${scheme.title} mb-4 cursor-pointer hover:underline-offset-2`}
        >
          {title}
        </h2>
        <button className="text-gray-400 hover:text-gray-300">
          {isExpanded ? (
            <FaChevronDown className="text-2xl" />
          ) : (
            <FaChevronUp className="text-2xl" />
          )}
        </button>
      </div>

      {isExpanded && (
        <div className="space-y-2">
          {projectList.map((project: SimpleProject, index: number) => {
            const uniqueId = `${colorScheme}_${project.name}_${index}`;

            const isSelected =
              selectionProject === project.name &&
              selectionPlatform === platform;
            const isIndexing = isProjectNotReady(project);

            return (
              <div
                key={uniqueId}
                className={`md:flex justify-between items-center p-4 rounded-lg transition-colors duration-200 border-b border-gray-700 last:border-b-0 ${
                  isSelected ? scheme.selected : "border-transparent"
                } ${
                  isIndexing
                    ? "cursor-not-allowed opacity-60"
                    : "cursor-pointer hover:bg-gray-700"
                }`}
                onClick={() => !isIndexing && handleProjectClick(project, true)}
              >
                <div className="flex items-center flex-1">
                  <div
                    className={`p-3 rounded-full mr-4 ${
                      isSelected ? "bg-white" : scheme.icon
                    }`}
                  >
                    <FaLightbulb
                      className={
                        isSelected ? scheme.iconSelected : "text-white"
                      }
                    />
                  </div>
                  <div className="flex-1">
                    <h3
                      className={`text-lg font-semibold ${
                        isSelected ? scheme.nameSelected : scheme.name
                      }`}
                    >
                      {project.name}
                    </h3>

                    <div className="lg:flex flex-row gap-2 text-xs text-gray-500">
                      <div className="lg:w-16">
                        Files: {project.input_files?.length || 0}
                      </div>
                      <div className="lg:w-32">
                        Status: {project.indexing_status}
                      </div>
                      <div className="">
                        Last update:{" "}
                        {project.updated_timestamp
                          .toLocaleString()
                          .replace(/.\d{4,}$/, "")}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Button to chat */}
                {!isIndexing && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation(); // Prevent triggering the project selection
                      e.preventDefault();
                      handleProjectClick(project, false);
                      setIsChatConfigDialogOpen(true, project);
                    }}
                    className="bg-blue-500 px-4 py-2 rounded-md w-full md:w-auto m-4 md:m-0"
                  >
                    <a href={`#`} className="!text-white">
                      Start Chat
                    </a>
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
