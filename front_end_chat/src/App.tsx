import "./App.css";
import AppWrapper from "./components/AppWrapper";
import ChatContainer from "./components/mainChat/ChatContainer";
import MarkdownDialogue from "./components/MarkdownDialogue";

function App() {
  return (
    <AppWrapper>
      <MarkdownDialogue />
      <ChatContainer />
    </AppWrapper>
  );
}

export default App;
