import { useState } from "react";
import { FaKey } from "react-icons/fa";
import { useNavigate } from "react-router-dom";
import { useShallow } from "zustand/shallow";
import LoginLayout from "./components/layout/LoginLayout";
import useChatStore from "./context/chatStore";
import { useDashboardStore } from "./context/dashboardStore";
import { validateToken } from "./lib/apiClient";
import { Role } from "./model/projectCategory";
import { UserData } from "./model/userData";

export default function Login() {
  const navigate = useNavigate();

  const { setJwt, setRole, jwt, role } = useChatStore(
    useShallow((state) => ({
      setJwt: state.setJwt,
      setRole: state.setRole,
      jwt: state.jwt,
      role: state.role,
    }))
  );

  const { setUserData } = useDashboardStore(
    useShallow((state) => ({
      setUserData: state.setUserData,
    }))
  );

  const [errorMessage, setErrorMessage] = useState("");
  const [token, setToken] = useState("");

  if (jwt && role != Role.TENNANT) {
    navigate("/dashboard");
    return null;
  }
  async function handleTokenValidation() {
    if (!token.trim()) {
      setErrorMessage("Please enter a token.");
      return;
    }

    try {
      const data = await validateToken(token);

      setJwt(token);
      setUserData(data as UserData);
      setRole(Role.TENNANT);
      setToken("");
      setErrorMessage("");

      navigate("/dashboard");
    } catch (error) {
      console.error("Token validation error:", error);
      setErrorMessage("Token validation failed. Please try again.");
    }
  }

  return (
    <LoginLayout title="Knowledge Base Dashboard">
      {/* Token Validation Section */}
      <div className="mb-6">
        <div className="mb-4">
          <label
            htmlFor="token"
            className="block text-sm font-medium text-gray-300 mb-2"
          >
            Enter Token
          </label>
          <input
            id="token"
            type="text"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="Enter your validation token"
            className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {errorMessage && (
          <div className="mb-4">
            <p className="text-red-500 text-sm">{errorMessage}</p>
          </div>
        )}

        <button
          onClick={handleTokenValidation}
          className="w-full cursor-pointer bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors duration-200 flex items-center justify-center space-x-3 shadow-lg hover:shadow-xl transform hover:scale-105 transition-all duration-200 mb-4"
        >
          <FaKey className="text-lg" />
          <span>Validate Token</span>
        </button>
      </div>

      {/* Footer */}
      <div className="mt-8 text-center">
        <p className="text-xs text-gray-500">
          Or login as Admin{" "}
          <a
            href="/admin"
            aria-label="Login as Admin"
            className="text-blue-500 hover:text-blue-600 cursor-pointer"
          >
            Admin
          </a>
        </p>
      </div>
    </LoginLayout>
  );
}
