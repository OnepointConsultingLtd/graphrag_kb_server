import { FaCog, FaEnvelope, FaSignOutAlt, FaUser } from "react-icons/fa";
import { useShallow } from "zustand/shallow";
import Admin from "./Admin";
import TennantLits from "./components/tennants/TennantLits";
import Modal from "./components/tennants/Actions/Modal";
import CreateTenantForm from "./components/tennants/Actions/CreateTenantForm";
import DeleteTenantForm from "./components/tennants/Actions/DeleteTenantForm";
import useChatStore from "./context/chatStore";
import useAdminStore from "./store/adminStore";
import decodedJwt from "./lib/decodeJwt";
import { Role } from "./model/projectCategory";
import { useState } from "react";

export default function Administrator() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [selectedTenant, setSelectedTenant] = useState<{
    folder_name: string;
    token: string;
  } | null>(null);

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

  const { deleteTenant } = useAdminStore(
    useShallow((state) => ({
      deleteTenant: state.deleteTenant,
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
  };

  const openModal = () => {
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
  };

  const openDeleteModal = (tenant: { folder_name: string; token: string }) => {
    setSelectedTenant(tenant);
    setIsDeleteModalOpen(true);
  };

  const closeDeleteModal = () => {
    setIsDeleteModalOpen(false);
    setSelectedTenant(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-blue-50 to-indigo-100 w-full">
      {/* Background Pattern */}
      <div className="absolute inset-0 opacity-20">
        <div
          className="absolute inset-0"
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23f3f4f6' fill-opacity='0.1'%3E%3Ccircle cx='30' cy='30' r='1'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
          }}
        ></div>
      </div>

      <div className="relative z-10">
        {/* Navigation Header */}
        <div className="bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-20">
          <div className="mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center py-4">
              <div className="flex items-center space-x-4">
                <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-blue-700 rounded-xl flex items-center justify-center shadow-lg">
                  <FaUser className="text-white text-lg" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-gray-900">
                    Administrator Dashboard
                  </h1>
                  <p className="text-sm text-gray-500">
                    Tenant Management System
                  </p>
                </div>
              </div>
              <button
                onClick={handleLogout}
                className="group relative inline-flex items-center px-4 py-2 bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white font-semibold rounded-lg shadow-md hover:shadow-lg transform hover:-translate-y-0.5 transition-all duration-200"
              >
                <FaSignOutAlt className="w-4 h-4 mr-2 group-hover:rotate-12 transition-transform duration-200" />
                <span>Logout</span>
              </button>
            </div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* User Profile Card */}
          <div className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-xl border border-gray-200 p-8 mb-8">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between">
              <div className="flex items-center space-x-6 mb-6 lg:mb-0">
                <div className="relative">
                  <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl flex items-center justify-center shadow-lg">
                    <FaUser className="text-white text-3xl" />
                  </div>
                  <div className="absolute -bottom-2 -right-2 w-8 h-8 bg-green-500 rounded-full flex items-center justify-center border-4 border-white">
                    <div className="w-3 h-3 bg-white rounded-full"></div>
                  </div>
                </div>
                <div>
                  <h2 className="text-3xl font-bold text-gray-900 mb-2">
                    {decodedJwt(jwt).name || "Administrator"}
                  </h2>
                  <p className="text-gray-600 flex items-center mb-3">
                    <FaEnvelope className="mr-2 text-sm" />
                    {decodedJwt(jwt).email || "admin@example.com"}
                  </p>
                  <div className="flex items-center space-x-3">
                    <span className="inline-flex items-center px-3 py-1 bg-green-100 text-green-800 text-sm font-medium rounded-full">
                      <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
                      Administrator
                    </span>
                    <span className="text-sm text-gray-500">
                      Last active: {new Date().toLocaleTimeString()}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Profile Information Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
            <div className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-lg border border-gray-200 p-6">
              <div className="flex items-center mb-4">
                <div className="w-10 h-10 bg-gradient-to-br from-blue-100 to-blue-200 rounded-xl flex items-center justify-center mr-3">
                  <FaUser className="text-blue-600" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900">
                  Full Name
                </h3>
              </div>
              <p className="text-gray-700 font-medium">
                {decodedJwt(jwt).name || "Administrator User"}
              </p>
            </div>

            <div className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-lg border border-gray-200 p-6">
              <div className="flex items-center mb-4">
                <div className="w-10 h-10 bg-gradient-to-br from-green-100 to-green-200 rounded-xl flex items-center justify-center mr-3">
                  <FaEnvelope className="text-green-600" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900">
                  Email Address
                </h3>
              </div>
              <p className="text-gray-700 font-medium">
                {decodedJwt(jwt).email}
              </p>
            </div>

            <div className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-lg border border-gray-200 p-6">
              <div className="flex items-center mb-4">
                <div className="w-10 h-10 bg-gradient-to-br from-purple-100 to-purple-200 rounded-xl flex items-center justify-center mr-3">
                  <FaCog className="text-purple-600" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900">
                  Last Login
                </h3>
              </div>
              <p className="text-gray-700 font-medium">
                {new Date().toLocaleDateString()} at{" "}
                {new Date().toLocaleTimeString()}
              </p>
            </div>
          </div>

          {/* Tennants Management */}
          <TennantLits
            onOpenModal={openModal}
            onOpenDeleteModal={openDeleteModal}
          />
        </div>
      </div>

      {/* Create Modal */}
      <Modal title="Create Tenant" isOpen={isModalOpen} onClose={closeModal}>
        <CreateTenantForm onSuccess={closeModal} onCancel={closeModal} />
      </Modal>

      {/* Delete Modal */}
      <Modal
        title="Delete Tenant"
        isOpen={isDeleteModalOpen}
        onClose={closeDeleteModal}
      >
        {selectedTenant && (
          <DeleteTenantForm
            tenantName={selectedTenant.folder_name}
            onConfirm={async () => {
              if (!jwt) return;
              try {
                await deleteTenant(jwt, {
                  tennant_folder: selectedTenant.folder_name,
                });
                closeDeleteModal();
              } catch (error) {
                console.error("Failed to delete tenant:", error);
              }
            }}
            onCancel={closeDeleteModal}
          />
        )}
      </Modal>
    </div>
  );
}
