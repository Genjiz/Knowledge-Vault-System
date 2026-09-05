import { StrictMode, Suspense } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider } from '@tanstack/react-router'
import { Toaster } from 'sonner'
import { queryClient } from '@/app/query-client'
import { router } from '@/app/router'
import '@/index.css'

createRoot(document.getElementById('app')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <Suspense fallback={<div className="app-loading">正在加载工作台...</div>}>
        <RouterProvider router={router} />
      </Suspense>
      <Toaster richColors position="top-right" />
    </QueryClientProvider>
  </StrictMode>,
)
