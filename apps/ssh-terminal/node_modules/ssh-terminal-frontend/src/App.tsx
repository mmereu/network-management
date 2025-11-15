import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { SSHTerminalPage } from './pages/SSHTerminalPage';
import { ConfigSwitchPage } from './pages/ConfigSwitchPage';

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<SSHTerminalPage />} />
          <Route path="/config-switch" element={<ConfigSwitchPage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
