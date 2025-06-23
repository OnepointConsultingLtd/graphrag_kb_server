import { useAuth0 } from "@auth0/auth0-react";
import { FaSignInAlt } from "react-icons/fa";

export default function Login() {
  const { error, loginWithRedirect } = useAuth0();

  const handleLogin = async () => {
    await loginWithRedirect({
      appState: {
        returnTo: "/dashboard",
      },
    });
  };

  if (error) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="bg-red-900 border border-red-700 text-red-100 px-6 py-4 rounded-lg">
          <h2 className="text-xl font-semibold mb-2">Authentication Error</h2>
          <p>{error.message}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        {/* Logo/Branding */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">GraphRAG</h1>
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

          {/* Single Login Button */}
          <button
            onClick={handleLogin}
            className="w-full cursor-pointer bg-blue-600 hover:bg-blue-700 text-white font-semibold py-4 px-6 rounded-lg transition-colors duration-200 flex items-center justify-center space-x-3 shadow-lg hover:shadow-xl transform hover:scale-105 transition-all duration-200"
          >
            <FaSignInAlt className="text-xl" />
            <span>Login</span>
          </button>

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
