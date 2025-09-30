import { useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useShallow } from "zustand/shallow";
import useChatStore from "../context/chatStore";

export default function PrivateRoute({
  children,
}: {
  children: React.ReactNode;
}) {
  const navigate = useNavigate();
  const location = useLocation();

  const { jwt } = useChatStore(
    useShallow((state) => ({
      jwt: state.jwt,
    }))
  );

  useEffect(() => {
    if (!jwt) {
      if (location.pathname === "/administrator") {
        navigate("/admin");
      } else {
        navigate("/login");
      }
    }
  }, [jwt, navigate, location.pathname]);

  if (!jwt) {
    return null;
  }

  return <>{children}</>;
}
