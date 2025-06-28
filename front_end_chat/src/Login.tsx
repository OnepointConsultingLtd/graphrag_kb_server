import { useState } from "react";
import { FaKey } from "react-icons/fa";
import { useShallow } from "zustand/shallow";
import useChatStore from "./context/chatStore";
import { useNavigate } from "react-router-dom";
import { UserData } from "./model/userData";
import { useDashboardStore } from "./context/dashboardStore";
import { validateToken } from "./lib/apiClient";

export default function Login() {

  const navigate = useNavigate();

  const { setJwt } = useChatStore(
    useShallow((state) => ({
      setJwt: state.setJwt,
    }))
  );

  const { setUserData } = useDashboardStore(
    useShallow((state) => ({
      setUserData: state.setUserData,
    }))
  );

  const [errorMessage, setErrorMessage] = useState("");
  const [token, setToken] = useState("");

  async function handleTokenValidation() {
    if (!token.trim()) {
      setErrorMessage("Please enter a token.");
      return;
    }

    try {
      const data = await validateToken(token);

      setJwt(token);
      setUserData(data as UserData);

      setToken("");
      setErrorMessage("");

      navigate("/dashboard");
    } catch (error) {
      console.error("Token validation error:", error);
      setErrorMessage("Token validation failed. Please try again.");
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        {/* Logo/Branding */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">
            Onepoint GraphRAG System
          </h1>
          <p className="text-gray-400">Knowledge Base Dashboard</p>
        </div>

        {/* Login Card */}
        <div className="bg-gray-800 rounded-lg p-8 shadow-xl border border-gray-700">
          <div className="text-center mb-6">
            <h2 className="text-2xl font-semibold text-white mb-2">
              Welcome Back
            </h2>
            <p className="text-gray-400">Sign in to access your dashboard</p>
          </div>

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
              By signing in, you agree to our Terms of Service and Privacy
              Policy
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
