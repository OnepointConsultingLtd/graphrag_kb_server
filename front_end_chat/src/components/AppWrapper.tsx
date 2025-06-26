import { useShallow } from "zustand/shallow";
import useChatStore from "../context/chatStore";
// import Login from "./Login";
import Login from "../Login";
import Dashboard from "../dashboard";

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
    return <Dashboard />;
  }

  return <>{children}</>;
}
