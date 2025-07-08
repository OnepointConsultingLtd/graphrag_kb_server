import Actions from "./Actions";
import UserProfile from "./UserProfile";
import CreateProjectModal from "./CreateProjectModal";
import Header from "./Header";
import ProjectList from "./ProjectList";
import DeleteConfirmation from "./DeleteConfirmation";
import GenerateSnippetModal from "./GenerateSnippetModal";
import ChatConfigDialog from "./ChatConfigDialog";
import GenerateURLModal from "./GenerateURLModal";

export default function Dashboard() {
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
