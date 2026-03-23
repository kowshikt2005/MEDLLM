import React from 'react';
import { Download } from 'lucide-react';

function Header() {
  const handleDownload = () => {
    console.log('Downloading conversation...');
  };

  return (
    <header className="bg-[#1A1C25] border-b border-gray-800 py-3">
      <div className="container mx-auto max-w-5xl px-4 flex justify-between items-center">
        <h1 className="text-xl font-semibold text-white">MedLLM</h1>
        <button 
          className="flex items-center gap-2 bg-[#27293a] text-white px-4 py-2 rounded-md border border-gray-700 hover:bg-[#2E3047] transition-colors"
          onClick={handleDownload}
        >
          <Download size={16} />
          <span>Download Chat</span>
        </button>
      </div>
    </header>
  );
}

export default Header;