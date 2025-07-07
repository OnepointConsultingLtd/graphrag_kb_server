

export default function ModalParent({ id, children }: { id: string, children: React.ReactNode }) {
    return <dialog id={id} className="modal">
        <div className="space-y-4 bg-gray-800 rounded-lg p-6 w-full max-w-2xl mx-4 overflow-y-auto max-h-[80vh]">
        {children}
        </div>
    </dialog>;
}