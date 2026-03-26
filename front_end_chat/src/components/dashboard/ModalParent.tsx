export default function ModalParent({
  id,
  children,
  onClose = () => {},
}: {
  id: string;
  children: React.ReactNode;
  onClose?: () => void;
}) {
  return (
    <dialog id={id} className="modal" onClose={onClose}>
      <div className="space-y-4 bg-gray-800 rounded-lg p-6 w-full max-w-2xl mx-4 overflow-y-auto max-h-[80vh]">
        {children}
      </div>
    </dialog>
  );
}
