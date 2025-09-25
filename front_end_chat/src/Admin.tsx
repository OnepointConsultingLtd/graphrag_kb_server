import { useState } from "react";
import { FaEnvelope, FaLock, FaUser } from "react-icons/fa";
import { useNavigate } from "react-router-dom";
import { useShallow } from "zustand/shallow";
import LoginLayout from "./components/layout/LoginLayout";
import { validateAdminToken } from "./lib/apiClient";
import useChatStore from "./context/chatStore";
import { useDashboardStore } from "./context/dashboardStore";
import { UserData } from "./model/userData";
import { Role } from "./model/projectCategory";

export default function Admin() {
  const navigate = useNavigate();

  const { setJwt, setRole } = useChatStore(
    useShallow((state) => ({
      setJwt: state.setJwt,
      setRole: state.setRole,
    }))
  );

  const { setUserData } = useDashboardStore(
    useShallow((state) => ({
      setUserData: state.setUserData,
    }))
  );

  const [errorMessage, setErrorMessage] = useState("");

  // Admin login form state
  const [adminForm, setAdminForm] = useState({
    name: "",
    email: "",
    password: "",
  });

  function handleAdminFormChange(e: React.ChangeEvent<HTMLInputElement>) {
    const { name, value } = e.target;
    setAdminForm((prev) => ({
      ...prev,
      [name]: value,
    }));
  }

  async function handleAdminLogin() {
    // Validate form fields
    if (
      !adminForm.name.trim() ||
      !adminForm.email.trim() ||
      !adminForm.password.trim()
    ) {
      setErrorMessage("Please fill in all fields.");
      return;
    }

    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(adminForm.email)) {
      setErrorMessage("Please enter a valid email address.");
      return;
    }

    try {
      const data = await validateAdminToken(
        adminForm.name,
        adminForm.email,
        adminForm.password
      );

      setJwt(data.token);
      setRole(Role.ADMIN);
      setUserData(data as UserData);

      setAdminForm({ name: "", email: "", password: "" });
      setErrorMessage("");

      navigate("/administrator");
    } catch (error) {
      console.error("Admin login error:", error);
      setErrorMessage(
        "Admin login failed. Please check your credentials and try again."
      );
    }
  }

  return (
    <LoginLayout title="Admin Login">
      {/* Admin Login Section */}
      <div className="mb-6">
        <div className="space-y-4">
          {/* Name Field */}
          <div>
            <label
              htmlFor="adminName"
              className="block text-sm font-medium text-gray-300 mb-2"
            >
              Full Name
            </label>
            <div className="relative">
              <FaUser className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 text-sm" />
              <input
                id="adminName"
                name="name"
                type="text"
                value={adminForm.name}
                onChange={handleAdminFormChange}
                placeholder="Enter your full name"
                className="w-full pl-10 pr-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>

          {/* Email Field */}
          <div>
            <label
              htmlFor="adminEmail"
              className="block text-sm font-medium text-gray-300 mb-2"
            >
              Email Address
            </label>
            <div className="relative">
              <FaEnvelope className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 text-sm" />
              <input
                id="adminEmail"
                name="email"
                type="email"
                value={adminForm.email}
                onChange={handleAdminFormChange}
                placeholder="Enter your email address"
                className="w-full pl-10 pr-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>

          {/* Password Field */}
          <div>
            <label
              htmlFor="adminPassword"
              className="block text-sm font-medium text-gray-300 mb-2"
            >
              Password
            </label>
            <div className="relative">
              <FaLock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 text-sm" />
              <input
                id="adminPassword"
                name="password"
                type="text"
                value={adminForm.password}
                onChange={handleAdminFormChange}
                placeholder="Enter your password"
                className="w-full pl-10 pr-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>
        </div>

        {errorMessage && (
          <div className="mt-4">
            <p className="text-red-500 text-sm">{errorMessage}</p>
          </div>
        )}

        <button
          onClick={handleAdminLogin}
          className="w-full cursor-pointer bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-lg flex items-center justify-center space-x-3 shadow-lg hover:shadow-xl transform hover:scale-105 transition-all duration-200 mt-6"
        >
          <FaUser className="text-lg" />
          <span>Admin Login</span>
        </button>
      </div>

      {/* Footer */}
      <div className="mt-8 text-center">
        <p className="text-xs text-gray-500">
          Or use Token{" "}
          <a
            href="/"
            aria-label="Token Login"
            className="text-blue-500 hover:text-blue-600 cursor-pointer"
          >
            Token Login
          </a>
        </p>
      </div>
    </LoginLayout>
  );
}
