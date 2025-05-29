import './App.css'
import useChatStore from './context/chatStore';
import Login from './components/Login';
import { useShallow } from 'zustand/react/shallow';
import ProjectSelector from './components/ProjectSelector';


function App() {
  const { jwt, selectedProject } = useChatStore(useShallow((state) => ({
    jwt: state.jwt,
    selectedProject: state.selectedProject,
  })));

  if (!jwt) {
    return <Login />
  }
  
  if (!selectedProject) {
    return <ProjectSelector />
  }

  return (
    <>
      
    </>
  )
}

export default App
