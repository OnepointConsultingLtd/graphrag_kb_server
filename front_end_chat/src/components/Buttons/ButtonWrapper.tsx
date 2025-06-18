import React from "react";

export default function ButtonWrapper({
  onClick,
  name,
  children,
}: {
  onClick: () => void;
  name: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex justify-start">
      <button onClick={onClick} className="btn btn-primary">
        {children}
        <span className="font-medium md:!block !hidden">{name}</span>
      </button>
    </div>
  );
}
