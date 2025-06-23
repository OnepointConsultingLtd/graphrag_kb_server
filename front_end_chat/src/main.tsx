import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.tsx";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import FloatingChat from "./FloatingChat.tsx";
import { AppComponent } from "./lib/appComponents.ts";
import type { Project } from "./model/projectCategory.ts";
import { Auth0Provider } from "@auth0/auth0-react";
import { getConfig } from "./config.ts";
import Login from "./Login.tsx";
import Dashboard from "./dashboard.tsx";

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

type AppState = {
  returnTo?: string;
};

const onRedirectCallback = (appState: AppState | undefined) => {
  const returnTo =
    appState && appState["returnTo"]
      ? appState["returnTo"]
      : window.location.pathname;

  window.location.href = returnTo;
};

const config = getConfig();

const providerConfig = {
  domain: config.domain,
  clientId: config.clientId,
  onRedirectCallback,
  authorizationParams: {
    redirect_uri: window.location.origin,
    ...(config.audience ? { audience: config.audience } : null),
  },
};

createRoot(
  document.getElementById(window.chatConfig?.rootElementId ?? "root")!
).render(
  <StrictMode>
    <BrowserRouter>
      <Auth0Provider {...providerConfig}>
        <div className="lg:container mx-auto">
          <Routes>
            <Route path="/" element={chooseComponent()} />
            <Route path="/floating-chat" element={<FloatingChat />} />
            <Route path="/login" element={<Login />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="*" element={chooseComponent()} />
          </Routes>
        </div>
      </Auth0Provider>
    </BrowserRouter>
  </StrictMode>
);
