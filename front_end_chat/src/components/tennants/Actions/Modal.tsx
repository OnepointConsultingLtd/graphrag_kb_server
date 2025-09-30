import { useEffect } from "react";
import { FaTimes } from "react-icons/fa";

type ModalProps = {
  title: string;
  children: React.ReactNode;
  isOpen: boolean;
  onClose: () => void;
  showCloseButton?: boolean;
};

export default function Modal({
  title,
  children,
  isOpen,
  onClose,
  showCloseButton = true,
}: ModalProps) {
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
      document.body.style.overflow = "hidden";
    }

    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "unset";
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto max-w-3xl mx-auto">
      <div
        className="fixed inset-0 bg-black/50 bg-opacity-50 backdrop-blur-sm transition-opacity duration-300"
        onClick={onClose}
      />

      {/* Modal Container */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div
          className={`relative w-full transform transition-all duration-300 scale-100 opacity-100`}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Modal Content */}
          <div className="relative bg-white rounded-2xl shadow-2xl border border-gray-200 overflow-hidden">
            {/* Header */}
            <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-4 border-b border-blue-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 bg-white bg-opacity-20 rounded-lg flex items-center justify-center">
                    <div className="w-4 h-4 bg-white rounded-sm"></div>
                  </div>
                  <h3 className="text-xl font-bold text-white">{title}</h3>
                </div>
                {showCloseButton && (
                  <button
                    onClick={onClose}
                    className="text-white hover:text-gray-200 transition-colors duration-200 p-1 rounded-lg hover:bg-white hover:bg-opacity-20"
                  >
                    <FaTimes className="w-5 h-5" />
                  </button>
                )}
              </div>
            </div>

            {/* Body */}
            <div className="p-6">{children}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
