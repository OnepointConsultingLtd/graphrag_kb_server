import { useAuth0 } from "@auth0/auth0-react";
import Actions from "./components/Dashboard/Actions";
import CreateProjectModal from "./components/Dashboard/CreateProjectModal";
import GenerateSnippetModal from "./components/Dashboard/GenerateSnippetModal";
import Header from "./components/Dashboard/Header";
import Loading from "./components/Loading";
import ProjectList from "./components/Dashboard/ProjectList";
import UserProfile from "./components/Dashboard/UserProfile";
import { useNavigate } from "react-router-dom";
import { useEffect } from "react";

export default function Dashboard() {
  const { isAuthenticated, isLoading } = useAuth0();
  const navigate = useNavigate();

  useEffect(() => {
    // Only redirect if not loading and not authenticated
    if (!isLoading && !isAuthenticated) {
      navigate("/login1");
    }
  }, [isAuthenticated, isLoading, navigate]);

  // Show loading while Auth0 is initializing
  if (isLoading) {
    return <Loading />;
  }

  // Don't render dashboard if not authenticated
  if (!isAuthenticated) {
    return null;
  }

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
