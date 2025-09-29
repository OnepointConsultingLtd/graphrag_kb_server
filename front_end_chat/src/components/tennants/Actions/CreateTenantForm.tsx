import { useState } from "react";
import {
  FaBuilding,
  FaSpinner,
  FaCheck,
  FaExclamationTriangle,
} from "react-icons/fa";
import { useShallow } from "zustand/shallow";
import useAdminStore from "../../../store/adminStore";
import useChatStore from "../../../context/chatStore";

type CreateTenantFormProps = {
  onSuccess?: () => void;
  onCancel?: () => void;
};

export default function CreateTenantForm({
  onSuccess,
  onCancel,
}: CreateTenantFormProps) {
  const [tenantName, setTenantName] = useState("");
  const [tenantEmail, setTenantEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState<
    "idle" | "success" | "error"
  >("idle");

  const { jwt } = useChatStore(
    useShallow((state) => ({
      jwt: state.jwt,
    }))
  );

  const { createTenant } = useAdminStore(
    useShallow((state) => ({
      createTenant: state.createTenant,
    }))
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!tenantName.trim() || !tenantEmail.trim() || !jwt) {
      setSubmitStatus("error");
      return;
    }

    setIsSubmitting(true);
    setSubmitStatus("idle");

    try {
      await createTenant(jwt, {
        tennant_name: tenantName.trim(),
        email: tenantEmail.trim(),
      });

      setSubmitStatus("success");
      setTenantName("");
      setTenantEmail("");

      // Call success callback and reset after 2 seconds
      setTimeout(() => {
        setSubmitStatus("idle");
        onSuccess?.();
      }, 2000);
    } catch (error) {
      console.error("Failed to create tenant:", error);
      setSubmitStatus("error");

      // Reset error status after 3 seconds
      setTimeout(() => {
        setSubmitStatus("idle");
      }, 3000);
    } finally {
      setIsSubmitting(false);
    }
  };

  const getStatusIcon = () => {
    if (isSubmitting) {
      return <FaSpinner className="w-4 h-4 animate-spin text-blue-600" />;
    }
    if (submitStatus === "success") {
      return <FaCheck className="w-4 h-4 text-green-600" />;
    }
    if (submitStatus === "error") {
      return <FaExclamationTriangle className="w-4 h-4 text-red-600" />;
    }
    return null;
  };

  const getStatusMessage = () => {
    if (submitStatus === "success") {
      return "Tenant created successfully!";
    }
    if (submitStatus === "error") {
      return "Failed to create tenant. Please try again.";
    }
    return null;
  };

  return (
    <div className="space-y-6">
      {/* Form Header */}
      <div className="text-center">
        <div className="w-16 h-16 bg-gradient-to-br from-blue-100 to-blue-200 rounded-full flex items-center justify-center mx-auto mb-4">
          <FaBuilding className="w-8 h-8 text-blue-600" />
        </div>
        <h4 className="text-lg font-semibold text-gray-900 mb-2">
          Create New Tenant
        </h4>
        <p className="text-sm text-gray-500">
          Set up a new tenant account with a unique identifier
        </p>
      </div>

      {/* Status Message */}
      {getStatusMessage() && (
        <div
          className={`p-4 rounded-lg border ${
            submitStatus === "success"
              ? "bg-green-50 border-green-200 text-green-800"
              : "bg-red-50 border-red-200 text-red-800"
          }`}
        >
          <div className="flex items-center space-x-2">
            {getStatusIcon()}
            <span className="text-sm font-medium">{getStatusMessage()}</span>
          </div>
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Tenant Email Field */}
        <div>
          <label
            htmlFor="tenantEmail"
            className="block text-sm font-semibold text-gray-700 mb-2"
          >
            Tenant Email <span className="text-red-500">*</span>
          </label>
          <input
            type="email"
            id="tenantEmail"
            value={tenantEmail}
            onChange={(e) => setTenantEmail(e.target.value)}
            placeholder="Enter tenant email"
            className="w-full px-4 text-gray-600 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
            disabled={isSubmitting}
            required
          />
        </div>

        {/* Tenant Name Field */}
        <div>
          <label
            htmlFor="tenantName"
            className="block text-sm font-semibold text-gray-700 mb-2"
          >
            Tenant Name <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            id="tenantName"
            value={tenantName}
            onChange={(e) => setTenantName(e.target.value)}
            placeholder="Enter tenant name"
            className="w-full px-4 text-gray-600 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
            disabled={isSubmitting}
            required
          />
        </div>

        {/* Action Buttons */}
        <div className="flex space-x-4 pt-4 border-t border-gray-200">
          <button
            type="submit"
            disabled={
              isSubmitting ||
              submitStatus === "success" ||
              !tenantName.trim() ||
              !tenantEmail.trim()
            }
            className="flex-1 cursor-pointer bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 disabled:from-gray-400 disabled:to-gray-500 text-white font-semibold py-3 px-6 rounded-xl shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all duration-200 disabled:transform-none disabled:shadow-lg flex items-center justify-center space-x-2"
          >
            {isSubmitting ? (
              <>
                <FaSpinner className="w-4 h-4 animate-spin" />
                <span>Creating...</span>
              </>
            ) : submitStatus === "success" ? (
              <>
                <FaCheck className="w-4 h-4" />
                <span>Created!</span>
              </>
            ) : (
              <span>Create Tenant</span>
            )}
          </button>

          <button
            type="button"
            disabled={isSubmitting}
            className="px-6 py-3 border border-gray-300 text-gray-700 font-semibold rounded-xl hover:bg-gray-50 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            onClick={onCancel}
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
