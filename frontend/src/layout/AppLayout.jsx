import { Outlet, useLocation } from 'react-router-dom';
import { Suspense } from 'react';
import { Sidebar } from '../components/Sidebar';
import TopBar from './TopBar';

function InlineLoader() {
  return (
    <div className="flex items-center justify-center py-20">
      <div className="w-6 h-6 border-2 border-gray-300 border-t-gray-900 rounded-full animate-spin" />
    </div>
  );
}

// Pages that should hide the global TopBar (they have their own header)
const PAGES_WITHOUT_TOPBAR = ['/tech-analysis', '/sentiment', '/twitter', '/trading', '/terminal'];

export default function AppLayout({ globalState }) {
  const location = useLocation();
  const hideTopBar = PAGES_WITHOUT_TOPBAR.some(path => location.pathname.startsWith(path));
  
  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      <Sidebar globalState={globalState} />

      <div className="flex-1 min-w-0 flex flex-col">
        {!hideTopBar && <TopBar />}
        <main className="flex-1 min-h-0 min-w-0 overflow-auto relative">
          <Suspense fallback={<InlineLoader />}>
            <Outlet />
          </Suspense>
        </main>
      </div>
    </div>
  );
}
