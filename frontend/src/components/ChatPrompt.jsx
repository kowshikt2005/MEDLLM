import React from 'react';
import { Stethoscope } from 'lucide-react';

function ChatPrompt() {
  return (
    <div className="text-center flex flex-col items-center">
      <div className="w-16 h-16 rounded-full bg-[#27293a] flex items-center justify-center mb-6">
        <Stethoscope className="text-white" size={36} />
      </div>
      <h2 className="text-3xl font-medium text-white">How can I assist with your medical questions?</h2>
      <p className="text-gray-400 mt-2">I provide general medical information. For specific medical advice, please consult a healthcare professional.</p>
    </div>
  );
}

export default ChatPrompt;