import { useNavigate } from "react-router-dom";
import { useShallow } from "zustand/shallow";
import useChatStore from "../context/chatStore";

export default function PrivateRoute({
  children,
}: {
  children: React.ReactNode;
}) {
  const navigate = useNavigate();

  const { jwt } = useChatStore(
    useShallow((state) => ({
      jwt: state.jwt,
    }))
  );

  if (!jwt) {
    navigate("/login");
    return null;
  }

  return <>{children}</>;
}
