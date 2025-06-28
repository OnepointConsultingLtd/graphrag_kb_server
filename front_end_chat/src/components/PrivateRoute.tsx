import { useShallow } from "zustand/shallow";
import useChatStore from "../context/chatStore";
import Login from "../Login";

export default function PrivateRoute({
  children,
}: {
  children: React.ReactNode;
}) {
  const { jwt } = useChatStore(
    useShallow((state) => ({
      jwt: state.jwt,
    }))
  );

  if (!jwt) {
    return <Login />;
  }

  return <>{children}</>;
}
