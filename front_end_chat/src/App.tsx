import { BrowserRouter, Route, Routes } from "react-router-dom";
import "./App.css";
import FloatingChat from "./FloatingChat";
import Login from "./Login";
import ChatRoute from "./components/ChatRoute";
import MarkdownDialogue from "./components/MarkdownDialogue";
import PrivateRoute from "./components/PrivateRoute";
import Dashboard from "./components/dashboard/Dashboard";
import ChatContainer from "./components/main-chat/ChatContainer";
import { AppComponent } from "./lib/appComponents";
import Admin from "./Admin";
import Administrator from "./Administrator";

function chooseComponent() {
  const widgetType = window.chatConfig?.widgetType;
  switch (widgetType) {
    case AppComponent.FLOATING_CHAT:
      return (
        <ChatRoute>
          <FloatingChat />
        </ChatRoute>
      );
    case AppComponent.CHAT:
      return (
        <ChatRoute>
          <ChatContainer />
        </ChatRoute>
      );
    case AppComponent.DASHBOARD:
      return (
        <PrivateRoute>
          <Dashboard />
        </PrivateRoute>
      );
    default:
      return (
        <PrivateRoute>
          <Dashboard />
        </PrivateRoute>
      );
  }
}

function App() {
  return (
    <div className="lg:container mx-auto">
      <MarkdownDialogue />
      <BrowserRouter>
        <Routes>
          <Route
            path="/floating-chat"
            element={
              <ChatRoute>
                <FloatingChat />
              </ChatRoute>
            }
          />
          <Route
            path="/chat"
            element={
              <ChatRoute>
                <ChatContainer />
              </ChatRoute>
            }
          />

          <Route path="/login" element={<Login />} />
          <Route path="/admin" element={<Admin />} />

          <Route
            path="/administrator"
            element={
              <PrivateRoute>
                <Administrator />
              </PrivateRoute>
            }
          />
          <Route
            path="/dashboard"
            element={
              <PrivateRoute>
                <Dashboard />
              </PrivateRoute>
            }
          />
          <Route path="*" element={chooseComponent()} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
