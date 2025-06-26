import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import App from "./App.tsx";
import Dashboard from "./dashboard.tsx";
import FloatingChat from "./FloatingChat.tsx";
import "./index.css";
import { AppComponent } from "./lib/appComponents.ts";
import Login from "./Login.tsx";
import type { Project } from "./model/projectCategory.ts";

declare global {
  interface Window {
    chatConfig: {
      widgetType: string;
      rootElementId: string;
      jwt?: string;
      project?: Project;
      displayFloatingChatIntro?: boolean;
      baseServer?: string;
      organisation_name?: string;
    };
  }
}

function chooseComponent() {
  const widgetType = window.chatConfig?.widgetType;
  switch (widgetType) {
    case AppComponent.FLOATING_CHAT:
      return <FloatingChat />;
    default:
      return <App />;
  }
}


createRoot(
  document.getElementById(window.chatConfig?.rootElementId ?? "root")!
).render(
  <StrictMode>
    <BrowserRouter>
        <div className="lg:container mx-auto">
          <Routes>
            <Route path="/" element={chooseComponent()} />
            <Route path="/floating-chat" element={<FloatingChat />} />
            <Route path="/login" element={<Login />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="*" element={chooseComponent()} />
          </Routes>
        </div>
    </BrowserRouter>
  </StrictMode>
);
