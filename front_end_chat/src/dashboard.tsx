import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Actions from "./components/Dashboard/Actions";
import CreateProjectModal from "./components/Dashboard/CreateProjectModal";
import GenerateSnippetModal from "./components/Dashboard/GenerateSnippetModal";
import Header from "./components/Dashboard/Header";
import ProjectList from "./components/Dashboard/ProjectList";
import UserProfile from "./components/Dashboard/UserProfile";

export default function Dashboard() {
  const navigate = useNavigate();

  const isTokenValidated = localStorage.getItem("tokenValidated") === "true";
  const token = localStorage.getItem("token");

  useEffect(() => {
    if (!isTokenValidated && !token) {
      navigate("/login1");
    }
  }, [isTokenValidated, token, navigate]);

  if (!isTokenValidated) {
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
