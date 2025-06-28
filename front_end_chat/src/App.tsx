import { BrowserRouter, Navigate, Route } from "react-router-dom";
import { Routes } from "react-router-dom";
import "./App.css";
import PrivateRoute from "./components/PrivateRoute";
import MarkdownDialogue from "./components/MarkdownDialogue";
import Dashboard from "./components/Dashboard/Dashboard";
import FloatingChat from "./FloatingChat";
import Login from "./Login";
import ChatContainer from "./components/mainChat/ChatContainer";
import { AppComponent } from "./lib/appComponents";
import ChatRoute from "./components/ChatRoute";


function chooseComponent() {
  const widgetType = window.chatConfig?.widgetType;
  switch (widgetType) {
    case AppComponent.FLOATING_CHAT:
      return <ChatRoute><FloatingChat /></ChatRoute>;
    case AppComponent.CHAT:
      return <ChatRoute><ChatContainer /></ChatRoute>;
    case AppComponent.DASHBOARD:
      return <PrivateRoute><Dashboard /></PrivateRoute>;
    default:
      return <PrivateRoute><Dashboard /></PrivateRoute>;
  }
}

function App() {
  return (
    <div className="lg:container mx-auto">
      <MarkdownDialogue />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={chooseComponent()} />
          <Route path="/floating-chat" element={<ChatRoute><FloatingChat /></ChatRoute>} />
          <Route path="/chat" element={<ChatRoute><ChatContainer /></ChatRoute>} />
          <Route path="/login" element={<Login />} />
          <Route path="/dashboard" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
          <Route path="*" element={chooseComponent()} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
