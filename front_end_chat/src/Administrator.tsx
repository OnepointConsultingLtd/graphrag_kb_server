import { useCallback, useEffect, useState } from "react";
import {
  FaCog,
  FaEnvelope,
  FaExternalLinkAlt,
  FaSignOutAlt,
  FaUser,
  FaUsers,
} from "react-icons/fa";
import { useShallow } from "zustand/shallow";
import Admin from "./Admin";
import useChatStore from "./context/chatStore";
import decodedJwt from "./lib/decodeJwt";
import { Role } from "./model/projectCategory";
import useAdminStore from "./store/adminStore";

export default function Administrator() {
  const [loading, setLoading] = useState(false);

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

  const { tennants, loadTennants } = useAdminStore(
    useShallow((state) => ({
      tennants: state.tennants,
      loadTennants: state.loadTennants,
    }))
  );

  console.log("tennantstennantstennants", tennants);

  const handleLoadTennants = useCallback(async () => {
    if (!jwt) return;
    setLoading(true);
    try {
      await loadTennants(jwt);
    } catch (error) {
      console.error("Failed to load tennants:", error);
    } finally {
      setLoading(false);
    }
  }, [jwt, loadTennants]);

  useEffect(() => {
    if (jwt && role === Role.ADMIN) {
      handleLoadTennants();
    }
  }, [jwt, role, handleLoadTennants]);
  console.log("decoded jwt", decodedJwt(jwt));

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
                  {decodedJwt(jwt).name || "Administrator"}
                </h1>
                <p className="text-gray-600 flex items-center">
                  <FaEnvelope className="mr-2 text-sm" />
                  {decodedJwt(jwt).email || "admin@example.com"}
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
                {decodedJwt(jwt).name || "Administrator User"}
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email Address
              </label>
              <p className="text-gray-900 bg-gray-50 p-3 rounded-lg">
                {decodedJwt(jwt).email}
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

        {/* Tennants Management */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center">
              <FaUsers className="text-gray-600 mr-2" />
              <h2 className="text-lg font-semibold text-gray-900">
                Tennants Management
              </h2>
            </div>
            <button
              onClick={handleLoadTennants}
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
            >
              <span>{loading ? "Loading..." : "Refresh"}</span>
            </button>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <span className="ml-2 text-gray-600">Loading tennants...</span>
            </div>
          ) : tennants && tennants.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Folder Name
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Created
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Token
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {tennants.map((tennant, index) => (
                    <tr
                      key={tennant.token || index}
                      className="hover:bg-gray-50"
                    >
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">
                          {tennant.folder_name}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">
                          {new Date(
                            tennant.creation_timestamp
                          ).toLocaleDateString()}
                        </div>
                        <div className="text-sm text-gray-500">
                          {new Date(
                            tennant.creation_timestamp
                          ).toLocaleTimeString()}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900 font-mono">
                          {tennant.token.substring(0, 8)}...
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <div className="flex space-x-2">
                          {tennant.chat_url && (
                            <a
                              href={tennant.chat_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-blue-600 hover:text-blue-900 flex items-center space-x-1"
                            >
                              <FaExternalLinkAlt className="text-xs" />
                              <span>Chat</span>
                            </a>
                          )}
                          {tennant.visualization_url && (
                            <a
                              href={tennant.visualization_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-green-600 hover:text-green-900 flex items-center space-x-1"
                            >
                              <FaExternalLinkAlt className="text-xs" />
                              <span>Viz</span>
                            </a>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-8">
              <FaUsers className="mx-auto h-12 w-12 text-gray-400 mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                No tennants found
              </h3>
              <p className="text-gray-500 mb-4">
                There are no tennants available. Click refresh to load tennants.
              </p>
              <button
                onClick={handleLoadTennants}
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg"
              >
                Load Tennants
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
