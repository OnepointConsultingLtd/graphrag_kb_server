import {
  FaCheckCircle,
  FaEnvelope,
  FaUser,
  FaSignOutAlt,
  FaFolder
} from "react-icons/fa";
import { useState, useEffect } from "react";
import Loading from "../Loading";

type UserData = {
  message: string;
  sub: string;
  name: string;
  iat: number;
  email: string;
};

export default function UserProfile() {
  const [userData, setUserData] = useState<UserData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const savedUserData = localStorage.getItem("userData");
    const isTokenValidated = localStorage.getItem("tokenValidated") === "true";

    if (savedUserData && isTokenValidated) {
      try {
        const parsedUserData = JSON.parse(savedUserData);
        setUserData(parsedUserData);
      } catch (error) {
        console.error("Error parsing user data:", error);
      }
    }
    setIsLoading(false);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("authToken");
    localStorage.removeItem("tokenValidated");
    localStorage.removeItem("userData");
    window.location.href = "/login";
  };

  if (isLoading) {
    return <Loading />;
  }

  if (!userData) return null;

  return (
    <div className="bg-gray-800 rounded-lg p-6 mb-6">
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
          <div className="w-16 h-16 rounded-full border-2 border-gray-600 bg-blue-600 flex items-center justify-center">
            <FaUser className="text-white text-xl" />
          </div>
        </div>

        {/* User Details */}
        <div className="flex-1 space-y-3">
          <div className="flex items-center space-x-2">
            <FaFolder className="text-gray-400" />
            <span className="font-medium">{userData.name || "User"}</span>
          </div>

          <div className="flex items-center space-x-2">
            <FaEnvelope className="text-gray-400" />
            <span className="text-gray-300">{userData.email}</span>
            <FaCheckCircle
              className="text-green-500 text-sm"
              title="Email verified"
            />
          </div>

          <div className="text-sm text-gray-400">
            <span className="font-medium">Sub:</span> {userData.sub}
          </div>

          <div className="text-xs text-gray-500">
            <span className="font-medium">Token Issued At:</span>{" "}
            {new Date(userData.iat * 1000).toLocaleString()}
          </div>
        </div>
      </div>
    </div>
  );
}
