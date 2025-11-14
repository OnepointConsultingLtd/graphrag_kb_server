import { FaSignOutAlt } from "react-icons/fa";


export default function LogoutButton({ handleLogout }: { handleLogout: () => void }) {
    return (
        <button
            onClick={handleLogout}
            className="group relative inline-flex items-center px-4 py-2 bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white font-semibold rounded-lg shadow-md hover:shadow-lg transform hover:-translate-y-0.5 transition-all duration-200"
        >
            <FaSignOutAlt className="w-4 h-4 mr-2 group-hover:rotate-12 transition-transform duration-200" />
            <span>Logout</span>
        </button>
    )
}