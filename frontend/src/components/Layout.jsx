import React from 'react';
import Header from './Header';

function Layout({ children }) {
  return (
    <div className="min-h-screen bg-[#1A1C25] text-white flex flex-col">
      <Header />
      <main className="flex-1 container mx-auto max-w-5xl px-4 py-6">
        {children}
      </main>
    </div>
  );
}

export default Layout;