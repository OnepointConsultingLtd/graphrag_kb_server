import { useAuth0 } from "@auth0/auth0-react";
import { FaCheckCircle, FaEnvelope, FaUser } from "react-icons/fa";

export default function UserProfile() {
  const { user, logout } = useAuth0();

  if (!user) return null;

  return (
    <div className="bg-gray-800 rounded-lg p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">User Profile</h2>
        <button
          onClick={() => logout()}
          className="btn btn-sm btn-outline btn-error"
        >
          Logout
        </button>
      </div>

      <div className="flex items-start space-x-4">
        {/* Profile Picture */}
        <div className="flex-shrink-0">
          <img
            src={user.picture}
            alt={user.name || "Profile"}
            className="w-16 h-16 rounded-full border-2 border-gray-600"
          />
        </div>

        {/* User Details */}
        <div className="flex-1 space-y-3">
          <div className="flex items-center space-x-2">
            <FaUser className="text-gray-400" />
            <span className="font-medium">{user.name}</span>
          </div>

          <div className="flex items-center space-x-2">
            <FaEnvelope className="text-gray-400" />
            <span className="text-gray-300">{user.email}</span>
            {user.email_verified && (
              <FaCheckCircle
                className="text-green-500 text-sm"
                title="Email verified"
              />
            )}
          </div>

          {user.nickname && (
            <div className="text-sm text-gray-400">
              <span className="font-medium">Nickname:</span> {user.nickname}
            </div>
          )}

          {user.given_name && user.family_name && (
            <div className="text-sm text-gray-400">
              <span className="font-medium">Full Name:</span> {user.given_name}{" "}
              {user.family_name}
            </div>
          )}

          <div className="text-xs text-gray-500">
            <span className="font-medium">User ID:</span> {user.sub}
          </div>
        </div>
      </div>
    </div>
  );
}
