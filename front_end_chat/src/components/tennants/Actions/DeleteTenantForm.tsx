import { useState } from "react";
import {
  FaTrash,
  FaSpinner,
  FaCheck,
  FaExclamationTriangle,
  FaExclamationCircle,
} from "react-icons/fa";
import { useShallow } from "zustand/shallow";
import useChatStore from "../../../context/chatStore";

type DeleteTenantFormProps = {
  tenantName: string;
  onConfirm: () => Promise<void>;
  onCancel: () => void;
};

export default function DeleteTenantForm({
  tenantName,
  onConfirm,
  onCancel,
}: DeleteTenantFormProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState<
    "idle" | "success" | "error"
  >("idle");

  const { jwt } = useChatStore(
    useShallow((state) => ({
      jwt: state.jwt,
    }))
  );

  const handleDelete = async () => {
    if (!jwt) {
      setSubmitStatus("error");
      return;
    }

    setIsSubmitting(true);
    setSubmitStatus("idle");

    try {
      await onConfirm();
      setSubmitStatus("success");

      // Reset success status after 2 seconds
      setTimeout(() => {
        setSubmitStatus("idle");
      }, 2000);
    } catch (error) {
      console.error("Failed to delete tenant:", error);
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
      return <FaSpinner className="w-4 h-4 animate-spin text-red-600" />;
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
      return "Tenant deleted successfully!";
    }
    if (submitStatus === "error") {
      return "Failed to delete tenant. Please try again.";
    }
    return null;
  };

  return (
    <div className="space-y-6">
      {/* Form Header */}
      <div className="text-center">
        <div className="w-16 h-16 bg-gradient-to-br from-red-100 to-red-200 rounded-full flex items-center justify-center mx-auto mb-4">
          <FaTrash className="w-8 h-8 text-red-600" />
        </div>
        <h4 className="text-lg font-semibold text-gray-900 mb-2">
          Delete Tenant
        </h4>
        <p className="text-sm text-gray-500">
          This action cannot be undone. All data associated with this tenant
          will be permanently removed.
        </p>
      </div>

      {/* Warning Message */}
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-start space-x-3">
          <FaExclamationCircle className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" />
          <div>
            <h5 className="text-sm font-semibold text-red-800 mb-1">
              Warning: This action is irreversible
            </h5>
            <p className="text-sm text-red-700">
              You are about to delete the tenant <strong>"{tenantName}"</strong>
              . This will permanently remove all associated data,
              configurations, and access rights.
            </p>
          </div>
        </div>
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

      {/* Action Buttons */}
      <div className="flex space-x-4 pt-4 border-t border-gray-200">
        <button
          onClick={handleDelete}
          disabled={isSubmitting || submitStatus === "success"}
          className="flex-1 cursor-pointer bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 disabled:from-gray-400 disabled:to-gray-500 text-white font-semibold py-3 px-6 rounded-xl shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all duration-200 disabled:transform-none disabled:shadow-lg flex items-center justify-center space-x-2"
        >
          {isSubmitting ? (
            <>
              <FaSpinner className="w-4 h-4 animate-spin" />
              <span>Deleting...</span>
            </>
          ) : submitStatus === "success" ? (
            <>
              <FaCheck className="w-4 h-4" />
              <span>Deleted!</span>
            </>
          ) : (
            <>
              <FaTrash className="w-4 h-4" />
              <span>Delete Tenant</span>
            </>
          )}
        </button>

        <button
          onClick={onCancel}
          disabled={isSubmitting}
          className="px-6 py-3 border border-gray-300 text-gray-700 font-semibold rounded-xl hover:bg-gray-50 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
