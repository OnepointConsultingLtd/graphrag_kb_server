export default function CenteredLayout({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center h-screen mx-4">
      <div className="w-full mb-2">
        <h2 className="border-b-1 border-gray-300 pb-2 mb-4">{title}</h2>
      </div>
      {children}
    </div>
  );
}
