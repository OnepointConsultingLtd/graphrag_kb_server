import './App.css'
import useChatStore from './context/chatStore';
import Login from './components/Login';
import { useShallow } from 'zustand/react/shallow';
import ProjectSelector from './components/ProjectSelector';
import ChatContainer from './components/mainChat/ChatContainer';
import MarkdownDialogue from './components/MarkdownDialogue';

function App() {
  const { jwt, selectedProject } = useChatStore(useShallow((state) => ({
    jwt: state.jwt,
    selectedProject: state.selectedProject,
  })));

  console.log("jwt", jwt);

  if (!jwt) {
    return <Login />
  }
  
  if (!selectedProject) {
    return <ProjectSelector />
  }

  return (
    <>
      <MarkdownDialogue />
      <ChatContainer />
    </>
  )
}

export default App
