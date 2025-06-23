import React from "react";
import { FaTimes } from "react-icons/fa";
import { useDashboardStore } from "../../context/dashboardStore";

type ModalProps = {
  title: string;
  children: React.ReactNode;
  isOpen: boolean;
};

export default function Modal({ title, children, isOpen }: ModalProps) {
  const { closeModal } = useDashboardStore();

  if (!isOpen) return null;

  return (
    <dialog open className="modal modal-open">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 bg-opacity-30 z-0"
        onClick={closeModal}
      />
      {/* Modal Content */}
      <div
        className="modal-box w-11/12 max-w-2xl bg-gray-800 text-white z-10 relative mx-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={closeModal}
          className="btn btn-sm btn-circle btn-ghost absolute right-2 top-2"
        >
          <FaTimes />
        </button>
        <h3 className="font-bold text-2xl mb-4">{title}</h3>
        {children}
      </div>
    </dialog>
  );
}
