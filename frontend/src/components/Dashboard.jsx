import React from 'react';
import { motion } from 'framer-motion';
import { Stethoscope, Brain, FileText, Activity, Users } from 'lucide-react';
import ChatView from './ChatView';

function Dashboard() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="min-h-screen bg-cyan-50"
    >
      <header className="bg-[#4f8684] text-white">
        <div className="container mx-auto px-4 py-6">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-4">
              <Stethoscope size={32} />
              <h1 className="text-2xl font-bold">MedLLM</h1>
            </div>
            <nav className="hidden md:flex space-x-8">
              <button className="hover:text-cyan-100 transition-colors">Dashboard</button>
              <button className="hover:text-cyan-100 transition-colors">History</button>
              <button className="hover:text-cyan-100 transition-colors">Settings</button>
            </nav>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-white p-6 rounded-xl shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-center space-x-4">
              <div className="bg-cyan-100 p-3 rounded-lg">
                <Brain className="text-[#4f8684]" size={24} />
              </div>
              <div>
                <h3 className="font-semibold text-gray-800">AI Diagnostics</h3>
                <p className="text-sm text-gray-500">Advanced medical analysis</p>
              </div>
            </div>
          </div>
          
          <div className="bg-white p-6 rounded-xl shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-center space-x-4">
              <div className="bg-cyan-100 p-3 rounded-lg">
                <FileText className="text-[#4f8684]" size={24} />
              </div>
              <div>
                <h3 className="font-semibold text-gray-800">Medical Records</h3>
                <p className="text-sm text-gray-500">Secure documentation</p>
              </div>
            </div>
          </div>
          
          <div className="bg-white p-6 rounded-xl shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-center space-x-4">
              <div className="bg-cyan-100 p-3 rounded-lg">
                <Activity className="text-[#4f8684]" size={24} />
              </div>
              <div>
                <h3 className="font-semibold text-gray-800">Health Tracking</h3>
                <p className="text-sm text-gray-500">Monitor your progress</p>
              </div>
            </div>
          </div>
          
          <div className="bg-white p-6 rounded-xl shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-center space-x-4">
              <div className="bg-cyan-100 p-3 rounded-lg">
                <Users className="text-[#4f8684]" size={24} />
              </div>
              <div>
                <h3 className="font-semibold text-gray-800">Care Team</h3>
                <p className="text-sm text-gray-500">Collaborative healthcare</p>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6">
          <ChatView />
        </div>
      </main>
    </motion.div>
  );
}

export default Dashboard;