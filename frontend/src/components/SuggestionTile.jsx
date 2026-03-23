import React from 'react';

function SuggestionTile({ title, description }) {
  return (
    <div className="bg-[#27293a] hover:bg-[#2E3047] rounded-lg p-6 cursor-pointer transition-all duration-200 border border-gray-800 hover:border-gray-700">
      <div className="font-medium text-lg text-white mb-1">{title}</div>
      <div className="text-gray-400 text-sm">{description}</div>
    </div>
  );
}

export default SuggestionTile;