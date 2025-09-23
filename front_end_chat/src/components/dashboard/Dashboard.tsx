import { useShallow } from "zustand/shallow";
import useChatStore from "../../context/chatStore";
import Actions from "./Actions";
import ChatConfigDialog from "./ChatConfigDialog";
import CreateProjectModal from "./CreateProjectModal";
import DeleteConfirmation from "./DeleteConfirmation";
import GenerateSnippetModal from "./GenerateSnippetModal";
import GenerateURLModal from "./GenerateURLModal";
import Header from "./Header";
import ProjectList from "./ProjectList";
import UserProfile from "./UserProfile";
import Login from "../../Login";

export default function Dashboard() {
  const { jwt } = useChatStore(
    useShallow((state) => ({
      jwt: state.jwt,
    }))
  );

  if (!jwt) {
    return <Login />;
  }

  console.log("jwt", jwt);
  return (
    <div className="min-h-screen bg-gray-900 text-white lg:p-6 p-2">
      <div className="lg:max-w-7xl mx-auto">
        <Header />
        <UserProfile />
        <Actions />
        <ProjectList />
      </div>

      <ChatConfigDialog />
      <CreateProjectModal />
      <GenerateSnippetModal />
      <GenerateURLModal />
      <DeleteConfirmation />
    </div>
  );
}
