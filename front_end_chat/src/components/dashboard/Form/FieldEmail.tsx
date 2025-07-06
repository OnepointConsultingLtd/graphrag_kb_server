import { useDashboardStore } from "../../../context/dashboardStore";
import { useShallow } from "zustand/shallow";
import RenderLabel from "./RenderLabel";

export default function FieldEmail() {
  const { email, setEmail } = useDashboardStore(
    useShallow((state) => ({
      email: state.email,
      setEmail: state.setEmail,
    })),
  );

  return (
    <div>
      <RenderLabel label="Email" />
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        className="input input-primary w-full bg-gray-700"
        required
      />
    </div>
  );
}
