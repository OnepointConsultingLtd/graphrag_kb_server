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
      <button onClick={onClick} className="btn btn-primary bg-[#0B2D72] border-[#0B2D72] !flex">
        {children}
        <span className="font-medium md:!block !hidden text-white">{name}</span>
      </button>
    </div>
  );
}
