import { useShallow } from "zustand/shallow";
import useChatStore from "../context/chatStore";
// import Login from "./Login";
import ProjectSelector from "./ProjectSelector";
import Login from "../Login";

export default function AppWrapper({
  children,
}: {
  children: React.ReactNode;
}) {
  const { jwt, selectedProject } = useChatStore(
    useShallow((state) => ({
      jwt: state.jwt,
      selectedProject: state.selectedProject,
    }))
  );

  if (!jwt) {
    return <Login />;
  }

  if (!selectedProject) {
    return <ProjectSelector />;
  }

  return <>{children}</>;
}
