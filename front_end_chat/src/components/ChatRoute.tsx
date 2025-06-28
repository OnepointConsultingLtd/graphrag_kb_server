import { useShallow } from "zustand/shallow";
import useChatStore from "../context/chatStore";
import Login from "../Login";
import Dashboard from "./Dashboard/Dashboard";

export default function ChatRoute({
  children,
}: {
  children: React.ReactNode;
}) {
  const { jwt, selectedProject, chatType } = useChatStore(
    useShallow((state) => ({
      jwt: state.jwt,
      selectedProject: state.selectedProject,
      chatType: state.chatType,
    }))
  );

  if (!jwt) {
    return <Login />;
  }

  if(!selectedProject || !chatType) {
    return <Dashboard />;
  }

  return <>{children}</>;
}
