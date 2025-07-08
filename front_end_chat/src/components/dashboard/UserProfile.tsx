import {
  FaCheckCircle,
  FaEnvelope,
  FaUser,
  FaSignOutAlt,
  FaFolder,
} from "react-icons/fa";
import { useState, useEffect } from "react";
import Loading from "../Loading";
import { useShallow } from "zustand/shallow";
import useChatStore from "../../context/chatStore";
import { useDashboardStore } from "../../context/dashboardStore";
import { useNavigate } from "react-router-dom";
import useProjectSelectionStore from "../../context/projectSelectionStore";

export default function UserProfile() {
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  const { logout } = useChatStore(
    useShallow((state) => ({
      logout: state.logout,
    }))
  );

  const { logout: logoutProjectSelection } = useProjectSelectionStore(
    useShallow((state) => ({
      logout: state.logout,
    }))
  );

  const { userData, logout: logoutDashboard } = useDashboardStore(
    useShallow((state) => ({
      userData: state.userData,
      logout: state.logout,
    }))
  );

  useEffect(() => {
    setIsLoading(false);
  }, []);

  const handleLogout = () => {
    logout();
    logoutProjectSelection();
    logoutDashboard();
    navigate("/login");
  };

  if (isLoading) {
    return <Loading />;
  }

  if (!userData) return null;

  return (
    <div className="bg-gray-800 rounded-lg p-4 lg:p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">User Profile</h2>
        <button
          onClick={handleLogout}
          className="btn btn-sm btn-outline btn-error flex items-center space-x-2"
        >
          <FaSignOutAlt />
          <span>Logout</span>
        </button>
      </div>

      <div className="flex items-start space-x-4">
        {/* Profile Picture */}
        <div className="flex-shrink-0">
          <div className="w-12 lg:w-16 h-12 lg:h-16 rounded-full border-2 border-gray-600 bg-blue-600 flex items-center justify-center">
            <FaUser className="text-white text-xl" />
          </div>
        </div>

        {/* User Details */}
        <div className="flex-1 space-y-3 lg:text-base !text-sm">
          <div className="flex items-center space-x-2">
            <FaFolder className="text-gray-400" />
            <span className="font-medium lg:text-base text-sm">
              {userData.name || "User"}
            </span>
          </div>

          <div className="flex items-center space-x-2">
            <FaEnvelope className="text-gray-400" />
            <span className="text-gray-300 lg:text-base text-sm">
              {userData.email}
            </span>
            <FaCheckCircle
              className="text-green-500 text-sm"
              title="Email verified"
            />
          </div>

          <div className="text-sm text-gray-400">
            <span className="font-medium">Sub:</span> {userData.sub}
          </div>
        </div>
      </div>
    </div>
  );
}
