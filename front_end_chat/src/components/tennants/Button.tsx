import React from "react";

export default function Button({
  onClick,
  disabled,
  children,
  color,
}: {
  onClick: () => void;
  disabled: boolean;
  children: React.ReactNode;
  color: string;
}) {
  return (
    <button onClick={onClick} disabled={disabled} className={`btn ${color}`}>
      {children}
    </button>
  );
}
