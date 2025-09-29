import { useCallback, useEffect, useState } from "react";
import { FaPlus, FaTrash, FaUsers } from "react-icons/fa";
import { useShallow } from "zustand/shallow";
import useChatStore from "../../context/chatStore";
import { Role } from "../../model/projectCategory";
import useAdminStore from "../../store/adminStore";

type TennantLitsProps = {
  onOpenModal: () => void;
};

export default function TennantLits({ onOpenModal }: TennantLitsProps) {
  const [loading, setLoading] = useState(false);

  const { jwt, role } = useChatStore(
    useShallow((state) => ({
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

  return (
    <div className="bg-white rounded-xl shadow-lg border border-gray-100 p-8 mb-8 backdrop-blur-sm bg-gradient-to-br from-white to-gray-50">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center space-x-4">
          <div className="p-3 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl shadow-lg">
            <FaUsers className="text-white text-xl" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-1">
              Tennants Management
            </h2>
            <p className="text-gray-500 text-sm">
              Manage and monitor your tenant accounts
            </p>
          </div>
        </div>
        <button
          onClick={handleLoadTennants}
          disabled={loading}
          className="group relative inline-flex items-center px-6 py-3 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 disabled:from-gray-400 disabled:to-gray-500 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all duration-200 disabled:transform-none disabled:shadow-lg"
        >
          <div className="flex items-center space-x-2">
            {loading ? (
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
            ) : (
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
            )}
            <span>{loading ? "Loading..." : "Refresh Data"}</span>
          </div>
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <div className="text-center">
            <div className="relative">
              <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-200 border-t-blue-600 mx-auto"></div>
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-6 h-6 bg-blue-600 rounded-full animate-pulse"></div>
              </div>
            </div>
            <p className="mt-4 text-gray-600 font-medium">
              Loading tennants...
            </p>
            <p className="text-sm text-gray-400">
              Please wait while we fetch the data
            </p>
          </div>
        </div>
      ) : tennants && tennants.length > 0 ? (
        <div className="overflow-hidden rounded-xl border border-gray-200 shadow-sm">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gradient-to-r from-gray-50 to-gray-100">
                <tr>
                  <th className="px-8 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    <div className="flex items-center space-x-2">
                      <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                      <span>Folder Name</span>
                    </div>
                  </th>
                  <th className="px-8 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    <div className="flex items-center space-x-2">
                      <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                      <span>Created</span>
                    </div>
                  </th>
                  <th className="px-8 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    <div className="flex items-center space-x-2">
                      <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                      <span>Token</span>
                    </div>
                  </th>
                  <th className="px-8 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    <div className="flex items-center space-x-2">
                      <div className="w-2 h-2 bg-orange-500 rounded-full"></div>
                      <span>Actions</span>
                    </div>
                  </th>
                </tr>
              </thead>

              <tbody className="bg-white divide-y divide-gray-100">
                {tennants.map((tennant, index) => (
                  <tr
                    key={tennant.token || index}
                    className="group hover:bg-gradient-to-r hover:from-blue-50 hover:to-indigo-50 transition-all duration-200 border-b border-gray-100"
                  >
                    <td className="px-8 py-6 whitespace-nowrap">
                      <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center shadow-md">
                          <span className="text-white font-bold text-sm">
                            {tennant.folder_name.charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <div>
                          <div className="text-sm font-semibold text-gray-900 capitalize">
                            {tennant.folder_name.replace("_", " ")}
                          </div>
                          <div className="text-xs text-gray-500">
                            Tenant Account
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-8 py-6 whitespace-nowrap">
                      <div className="flex flex-col space-y-1">
                        <div className="text-sm font-medium text-gray-900">
                          {new Date(
                            tennant.creation_timestamp
                          ).toLocaleDateString()}
                        </div>
                        <div className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded-full inline-block w-fit">
                          {new Date(
                            tennant.creation_timestamp
                          ).toLocaleTimeString()}
                        </div>
                      </div>
                    </td>
                    <td className="px-8 py-6 whitespace-nowrap">
                      <div className="flex items-center space-x-2">
                        <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                        <div className="text-sm font-mono text-gray-700 bg-gray-100 px-3 py-1 rounded-lg">
                          {tennant.token.substring(0, 8)}...
                        </div>
                      </div>
                    </td>
                    <td className="px-8 py-6 whitespace-nowrap text-sm font-medium">
                      <div className="flex space-x-3">
                        <button
                          onClick={onOpenModal}
                          className="group/btn cursor-pointer inline-flex items-center px-4 py-2 text-xs font-semibold text-white bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 rounded-lg shadow-md hover:shadow-lg transform hover:-translate-y-0.5 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                        >
                          <FaPlus className="w-3 h-3 mr-2 group-hover/btn:rotate-90 transition-transform duration-200" />
                          <span>Create</span>
                        </button>

                        <button
                          onClick={() => {
                            // TODO: Implement delete functionality
                            console.log("Delete tenant:", tennant.folder_name);
                          }}
                          className="group/btn cursor-pointer inline-flex items-center px-4 py-2 text-xs font-semibold text-white bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 rounded-lg shadow-md hover:shadow-lg transform hover:-translate-y-0.5 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
                        >
                          <FaTrash className="w-3 h-3 mr-2 group-hover/btn:scale-110 transition-transform duration-200" />
                          <span>Delete</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="text-center py-16">
          <div className="relative">
            <div className="w-24 h-24 bg-gradient-to-br from-gray-100 to-gray-200 rounded-full flex items-center justify-center mx-auto mb-6 shadow-lg">
              <FaUsers className="h-12 w-12 text-gray-400" />
            </div>
            <div className="absolute -top-2 -right-2 w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
              <span className="text-white text-xs font-bold">0</span>
            </div>
          </div>
          <h3 className="text-2xl font-bold text-gray-900 mb-3">
            No tennants found
          </h3>
          <p className="text-gray-500 mb-8 max-w-md mx-auto">
            There are no tennants available in your system. Click the button
            below to load tennants or create a new one.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <button
              onClick={handleLoadTennants}
              className="group inline-flex items-center px-6 py-3 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all duration-200"
            >
              <svg
                className="w-4 h-4 mr-2 group-hover:rotate-180 transition-transform duration-300"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
              Load Tennants
            </button>
            <button
              onClick={onOpenModal}
              className="group inline-flex items-center px-6 py-3 bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all duration-200"
            >
              <FaPlus className="w-4 h-4 mr-2 group-hover:rotate-90 transition-transform duration-200" />
              Create New Tenant
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
