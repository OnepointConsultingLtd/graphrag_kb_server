import { FaCog, FaEnvelope, FaSignOutAlt, FaUser } from "react-icons/fa";
import { useNavigate } from "react-router-dom";
import { useShallow } from "zustand/shallow";
import Admin from "./Admin";
import useChatStore from "./context/chatStore";
import { useDashboardStore } from "./context/dashboardStore";
import { Role } from "./model/projectCategory";

export default function Administrator() {
  const navigate = useNavigate();

  const {
    logout: chatLogout,
    jwt,
    role,
  } = useChatStore(
    useShallow((state) => ({
      logout: state.logout,
      jwt: state.jwt,
      role: state.role,
    }))
  );

  const { userData, logout: dashboardLogout } = useDashboardStore(
    useShallow((state) => ({
      userData: state.userData,
      logout: state.logout,
    }))
  );

  if (!!jwt && role != Role.ADMIN) {
    return (
      <div className="min-h-screen lg:p-6 p-2 flex items-center justify-center">
        <p className="mr-2">
          You are not authorized to access this page, please login as a admin to
          access this page.
        </p>{" "}
        <br />
        <a href="/admin" className="text-blue-500" onClick={chatLogout}>
          {" > "}
          Admin Login
        </a>
      </div>
    );
  }

  if (!jwt) {
    return <Admin />;
  }

  const handleLogout = () => {
    chatLogout();
    dashboardLogout();
    navigate("/admin");
  };

  return (
    <div className="w-full h-full bg-gray-50 min-h-screen">
      <div className="mx-auto p-6">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex justify-between items-start">
            <div className="flex items-center space-x-4">
              <div className="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center">
                <FaUser className="text-white text-2xl" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  {userData?.name || "Administrator"}
                </h1>
                <p className="text-gray-600 flex items-center">
                  <FaEnvelope className="mr-2 text-sm" />
                  {userData?.email || "admin@example.com"}
                </p>
                <span className="inline-block bg-green-100 text-green-800 text-xs px-2 py-1 rounded-full mt-2">
                  Administrator
                </span>
              </div>
            </div>
            <div className="flex space-x-3">
              <button
                onClick={handleLogout}
                className="bg-red-600 cursor-pointer hover:bg-red-700 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
              >
                <FaSignOutAlt className="text-sm" />
                <span>Logout</span>
              </button>
            </div>
          </div>
        </div>

        {/* Profile Information */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex items-center mb-4">
            <FaCog className="text-gray-600 mr-2" />
            <h2 className="text-lg font-semibold text-gray-900">
              Profile Information
            </h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Full Name
              </label>
              <p className="text-gray-900 bg-gray-50 p-3 rounded-lg">
                {userData?.name || "Administrator User"}
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email Address
              </label>
              <p className="text-gray-900 bg-gray-50 p-3 rounded-lg">
                {userData?.email || "admin@example.com"}
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Role
              </label>
              <p className="text-gray-900 bg-gray-50 p-3 rounded-lg">
                System Administrator
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Last Login
              </label>
              <p className="text-gray-900 bg-gray-50 p-3 rounded-lg">
                {new Date().toLocaleDateString()} at{" "}
                {new Date().toLocaleTimeString()}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
