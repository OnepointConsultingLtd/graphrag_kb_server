import Actions from "./Actions";
import CreateProjectModal from "./CreateProjectModal";
import GenerateSnippetModal from "./GenerateSnippetModal";
import Header from "./Header";
import ProjectList from "./ProjectList";
import UserProfile from "./UserProfile";

export default function Dashboard() {
  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <div className="lg:max-w-7xl mx-auto">
        <Header />
        <UserProfile />
        <Actions />
        <ProjectList />
      </div>

      <CreateProjectModal />
      <GenerateSnippetModal />
    </div>
  );
}
