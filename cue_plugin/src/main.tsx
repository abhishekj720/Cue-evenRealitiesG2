import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// StrictMode is intentionally omitted: it double-mounts components in dev,
// which spawns duplicate WebSocket connections on every reload. The plugin's
// WS client is intentionally single-instance.
createRoot(document.getElementById('root')!).render(<App />)
