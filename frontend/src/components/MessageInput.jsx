import React, { useState } from 'react';
import { Send, Sparkles, Square } from 'lucide-react';

function MessageInput() {
  const [message, setMessage] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim()) {
      console.log('Sending message:', message);
      setMessage('');
    }
  };

  return (
    <div className="mt-auto">
      <form onSubmit={handleSubmit} className="relative">
        <div className="rounded-lg bg-[#27293a] border border-gray-700 overflow-hidden">
          <textarea 
            className="w-full bg-transparent px-4 py-3 resize-none focus:outline-none text-white placeholder-gray-400"
            placeholder="Send a message"
            rows="1"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
          />
          <div className="flex justify-between items-center px-3 py-2 border-t border-gray-700">
            <button type="button" className="text-gray-400 hover:text-white transition-colors">
              <Sparkles size={20} />
            </button>
            <div className="flex gap-2">
              <button 
                type="submit" 
                className={`rounded-md p-2 ${message.trim() ? 'bg-[#5D5FEF] text-white' : 'bg-gray-700 text-gray-400'} transition-colors`}
                disabled={!message.trim()}
              >
                <Send size={18} />
              </button>
            </div>
          </div>
        </div>
      </form>
    </div>
  );
}

export default MessageInput;