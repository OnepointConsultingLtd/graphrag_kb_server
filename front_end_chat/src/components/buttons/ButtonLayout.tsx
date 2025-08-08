export function ButtonLayout({ children }: { children: React.ReactNode }) {
  return (
    <div
      className={`grid overflow-x-hidden grid-cols-1 md:grid-cols-2 w-full gap-3`}
    >
      {children}
    </div>
  );
}
