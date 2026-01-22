import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import "./global.css"
import "filepond/dist/filepond.min.css"
import { ThemeProvider } from './components/theme-provider.tsx'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider defaultTheme='dark' storageKey='stemu-theme'>
      <App></App>
    </ThemeProvider>
  </React.StrictMode>
)
