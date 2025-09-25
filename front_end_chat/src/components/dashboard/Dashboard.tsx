import { useShallow } from "zustand/shallow";
import useChatStore from "../../context/chatStore";
import { Role } from "../../model/projectCategory";
import Actions from "./Actions";
import ChatConfigDialog from "./ChatConfigDialog";
import CreateProjectModal from "./CreateProjectModal";
import DeleteConfirmation from "./DeleteConfirmation";
import GenerateSnippetModal from "./GenerateSnippetModal";
import GenerateURLModal from "./GenerateURLModal";
import Header from "./Header";
import ProjectList from "./ProjectList";
import UserProfile from "./UserProfile";

export default function Dashboard() {
  const { jwt, role, logout } = useChatStore(
    useShallow((state) => ({
      jwt: state.jwt,
      role: state.role,
      logout: state.logout,
    }))
  );

  if (!!jwt && role != Role.TENNANT) {
    return (
      <div className="min-h-screen lg:p-6 p-2 flex items-center justify-center">
        <p className="mr-2">
          You are not authorized to access this page, please login as a tennant{" "}
          to access this page.
        </p>{" "}
        <br />
        <a href="/login" className="text-blue-500" onClick={logout}>
          {" > "}
          Login
        </a>
      </div>
    );
  }

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
