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
      <button onClick={onClick} className="btn btn-primary !flex">
        {children}
        <span className="font-medium md:!block !hidden text-white">{name}</span>
      </button>
    </div>
  );
}
