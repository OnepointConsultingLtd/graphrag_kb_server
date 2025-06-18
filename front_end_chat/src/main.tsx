import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.tsx";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import FloatingChat from "./FloatingChat.tsx";
import { AppComponent } from "./lib/appComponents.ts";
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
      <div className="lg:w-[1280px]">
        <Routes>
          <Route path="/" element={chooseComponent()} />
          <Route path="/floating-chat" element={<FloatingChat />} />
          <Route path="*" element={chooseComponent()} />
        </Routes>
      </div>
    </BrowserRouter>
  </StrictMode>
);
