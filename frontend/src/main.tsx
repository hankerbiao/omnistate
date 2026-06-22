import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { ThemeProvider } from 'next-themes'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Toaster } from './components/ui/sonner'
import './index.css'
import App from './App.tsx'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

// Global error handler: all unhandled query errors auto-toast
queryClient.getQueryCache().subscribe((event) => {
  if (event.type === 'updated' && event.action.type === 'error') {
    const error = event.action.error
    const message = error instanceof Error ? error.message : '请求失败，请稍后重试'
    toast.error(message)
  }
})

// Global error handler: all unhandled mutation errors auto-toast
queryClient.getMutationCache().subscribe((event) => {
  if (event.type === 'updated' && event.action.type === 'error') {
    const error = event.action.error
    const message = error instanceof Error ? error.message : '操作失败，请稍后重试'
    toast.error(message)
  }
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider attribute="data-theme" defaultTheme="light">
        <App />
        <Toaster position="top-right" richColors closeButton />
      </ThemeProvider>
    </QueryClientProvider>
  </StrictMode>,
)
