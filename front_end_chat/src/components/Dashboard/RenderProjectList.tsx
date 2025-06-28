import { FaLightbulb } from "react-icons/fa";
import { useShallow } from "zustand/shallow";
import useProjectSelectionStore from "../../context/projectSelectionStore";
import useChatStore from "../../context/chatStore";
import { Platform, SimpleProject, SearchType } from "../../model/projectCategory";
import ChatConfigDialog from "./ChatConfigDialog";

type RenderProjectListProps = {
  title: string;
  projectList: SimpleProject[];
  colorScheme: "blue" | "green";
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
    isChatConfigDialogOpen,
    setIsChatConfigDialogOpen,
  } = useProjectSelectionStore(
    useShallow((state) => ({
      selectionProject: state.selectionProject,
      selectionPlatform: state.selectionPlatform,
      setSelectionProjectAndPlatform: state.setSelectionProjectAndPlatform,
      isChatConfigDialogOpen: state.isChatConfigDialogOpen,
      setIsChatConfigDialogOpen: state.setIsChatConfigDialogOpen,
    }))
  );

  const { setSelectedProject } = useChatStore(
    useShallow((state) => ({
      setSelectedProject: state.setSelectedProject,
    }))
  );

  if (!projectList || projectList.length === 0) return null;

  const scheme = colors[colorScheme];

  const handleProjectClick = (project: SimpleProject) => {
    const isCurrentlySelected =
      selectionProject === project.name && selectionPlatform === platform;
    console.log("Project clicked:", isCurrentlySelected);
    setSelectionProjectAndPlatform(project.name, platform);

    if (isCurrentlySelected) {
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

  return (
    <div className="mb-8">
      <h2 className={`text-xl font-bold ${scheme.title} mb-4`}>{title}</h2>
      <div className="space-y-2">
        {projectList.map((project: SimpleProject, index: number) => {
          const uniqueId = `${colorScheme}_${project.name}_${index}`;

          const isSelected =
            selectionProject === project.name && selectionPlatform === platform;

          return (
            <div
              key={uniqueId}
              className={`flex justify-between items-center p-4 rounded-lg cursor-pointer hover:bg-gray-700 transition-colors duration-200 border-b border-gray-700 last:border-b-0 ${
                isSelected ? scheme.selected : "border-transparent"
              }`}
              onClick={() => handleProjectClick(project)}
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
                onClick={(e) => {
                  e.stopPropagation(); // Prevent triggering the project selection
                  handleProjectClick(project)
                  setIsChatConfigDialogOpen(true, project);
                }}
                className="bg-blue-500 px-4 py-2 rounded-md"
              >
                <a href={`#`} className="!text-white">
                  Start Chat
                </a>
              </button>
            </div>
          );
        })}
      </div>
      {isChatConfigDialogOpen && <ChatConfigDialog />}
    </div>
  );
}
