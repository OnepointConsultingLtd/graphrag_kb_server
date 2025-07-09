import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./index.css";
import type { Project } from "./model/projectCategory.ts";

declare global {
  interface Window {
    chatConfig: {
      widgetType: string;
      rootElementId: string;
      token?: string;
      project?: Project;
      displayFloatingChatIntro?: boolean;
      baseServer?: string;
      websocketServer?: string;
      organisation_name?: string;
    };
  }
}

createRoot(
  document.getElementById(window.chatConfig?.rootElementId ?? "root")!,
).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
