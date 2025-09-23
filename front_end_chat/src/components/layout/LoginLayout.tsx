import React from "react";

export default function LoginLayout({
  children,
  title,
}: {
  children: React.ReactNode;
  title: string;
}) {
  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        {/* Logo/Branding */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">
            Onepoint AI Engine
          </h1>
          <p className="text-gray-400">
            {title === "Admin Login"
              ? "Admin Dashboard"
              : "Knowledge Base Dashboard"}
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-gray-800 rounded-lg p-8 shadow-xl border border-gray-700">
          <div className="text-center mb-6">
            <h2 className="text-2xl font-semibold text-white mb-2">
              {title === "Admin Login" ? "Admin Access" : "Welcome Back"}
            </h2>
            <p className="text-gray-400">
              {title === "Admin Login"
                ? "Sign in with admin credentials"
                : "Sign in to access your dashboard"}
            </p>
          </div>

          {children}
        </div>
      </div>
    </div>
  );
}
