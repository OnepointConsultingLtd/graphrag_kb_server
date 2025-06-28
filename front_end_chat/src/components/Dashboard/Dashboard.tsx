import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Actions from "./Actions";
import CreateProjectModal from "./CreateProjectModal";
import GenerateSnippetModal from "./GenerateSnippetModal";
import Header from "./Header";
import ProjectList from "./ProjectList";
import UserProfile from "./UserProfile";
import useChatStore from "../../context/chatStore";
import { useShallow } from "zustand/shallow";

export default function Dashboard() {
  const { jwt } = useChatStore(
    useShallow((state) => ({
      jwt: state.jwt,
    }))
  );
  const navigate = useNavigate();

  const isTokenValidated = jwt.length > 0;
  const token = localStorage.getItem("chat-store");

  useEffect(() => {
    if (!isTokenValidated && !token) {
      navigate("/login");
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
