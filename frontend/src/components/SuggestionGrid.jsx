import React from 'react';
import SuggestionTile from './SuggestionTile';

function SuggestionGrid({ suggestions }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full max-w-3xl">
      {suggestions.map((suggestion, index) => (
        <SuggestionTile 
          key={index}
          title={suggestion.title}
          description={suggestion.description}
        />
      ))}
    </div>
  );
}

export default SuggestionGrid;