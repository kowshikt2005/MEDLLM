import React, { useState } from 'react';
import { motion } from 'framer-motion';
import Navbar from './Navbar';
import { Save, User, Heart, Activity, Weight, Ruler } from 'lucide-react';

function UserProfile() {
  const [formData, setFormData] = useState({
    fullName: '',
    age: '',
    gender: '',
    height: '',
    weight: '',
    bloodType: '',
    allergies: '',
    medications: '',
    conditions: '',
    lifestyle: '',
    exerciseFrequency: '',
    smokingStatus: '',
    alcoholConsumption: '',
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    // Handle form submission
    console.log(formData);
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  return (
    <div className="min-h-screen bg-cyan-50">
      <Navbar />
      
      <div className="container mx-auto px-4 py-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-4xl mx-auto"
        >
          <div className="bg-white rounded-2xl shadow-lg p-8">
            <div className="flex items-center space-x-4 mb-8">
              <div className="w-12 h-12 bg-[#4f8684] rounded-full flex items-center justify-center">
                <User className="text-white" size={24} />
              </div>
              <h1 className="text-3xl font-bold text-gray-900">Health Profile</h1>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Basic Information */}
              <section className="space-y-4">
                <h2 className="text-xl font-semibold text-gray-800 flex items-center">
                  <User size={20} className="mr-2" />
                  Basic Information
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <input
                    type="text"
                    name="fullName"
                    placeholder="Full Name"
                    value={formData.fullName}
                    onChange={handleChange}
                    className="w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#4f8684]"
                  />
                  <input
                    type="number"
                    name="age"
                    placeholder="Age"
                    value={formData.age}
                    onChange={handleChange}
                    className="w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#4f8684]"
                  />
                  <select
                    name="gender"
                    value={formData.gender}
                    onChange={handleChange}
                    className="w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#4f8684]"
                  >
                    <option value="">Select Gender</option>
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                    <option value="other">Other</option>
                  </select>
                  <select
                    name="bloodType"
                    value={formData.bloodType}
                    onChange={handleChange}
                    className="w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#4f8684]"
                  >
                    <option value="">Blood Type</option>
                    <option value="A+">A+</option>
                    <option value="A-">A-</option>
                    <option value="B+">B+</option>
                    <option value="B-">B-</option>
                    <option value="O+">O+</option>
                    <option value="O-">O-</option>
                    <option value="AB+">AB+</option>
                    <option value="AB-">AB-</option>
                  </select>
                </div>
              </section>

              {/* Physical Measurements */}
              <section className="space-y-4">
                <h2 className="text-xl font-semibold text-gray-800 flex items-center">
                  <Ruler size={20} className="mr-2" />
                  Physical Measurements
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <input
                    type="number"
                    name="height"
                    placeholder="Height (cm)"
                    value={formData.height}
                    onChange={handleChange}
                    className="w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#4f8684]"
                  />
                  <input
                    type="number"
                    name="weight"
                    placeholder="Weight (kg)"
                    value={formData.weight}
                    onChange={handleChange}
                    className="w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#4f8684]"
                  />
                </div>
              </section>

              {/* Medical History */}
              <section className="space-y-4">
                <h2 className="text-xl font-semibold text-gray-800 flex items-center">
                  <Heart size={20} className="mr-2" />
                  Medical History
                </h2>
                <div className="space-y-4">
                  <textarea
                    name="allergies"
                    placeholder="Allergies (if any)"
                    value={formData.allergies}
                    onChange={handleChange}
                    className="w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#4f8684]"
                    rows="2"
                  />
                  <textarea
                    name="medications"
                    placeholder="Current Medications"
                    value={formData.medications}
                    onChange={handleChange}
                    className="w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#4f8684]"
                    rows="2"
                  />
                  <textarea
                    name="conditions"
                    placeholder="Pre-existing Conditions"
                    value={formData.conditions}
                    onChange={handleChange}
                    className="w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#4f8684]"
                    rows="2"
                  />
                </div>
              </section>

              {/* Lifestyle */}
              <section className="space-y-4">
                <h2 className="text-xl font-semibold text-gray-800 flex items-center">
                  <Activity size={20} className="mr-2" />
                  Lifestyle
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <select
                    name="exerciseFrequency"
                    value={formData.exerciseFrequency}
                    onChange={handleChange}
                    className="w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#4f8684]"
                  >
                    <option value="">Exercise Frequency</option>
                    <option value="sedentary">Sedentary</option>
                    <option value="light">Light (1-2 days/week)</option>
                    <option value="moderate">Moderate (3-4 days/week)</option>
                    <option value="active">Active (5+ days/week)</option>
                  </select>
                  <select
                    name="smokingStatus"
                    value={formData.smokingStatus}
                    onChange={handleChange}
                    className="w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#4f8684]"
                  >
                    <option value="">Smoking Status</option>
                    <option value="never">Never Smoked</option>
                    <option value="former">Former Smoker</option>
                    <option value="current">Current Smoker</option>
                  </select>
                  <select
                    name="alcoholConsumption"
                    value={formData.alcoholConsumption}
                    onChange={handleChange}
                    className="w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#4f8684]"
                  >
                    <option value="">Alcohol Consumption</option>
                    <option value="none">None</option>
                    <option value="occasional">Occasional</option>
                    <option value="moderate">Moderate</option>
                    <option value="frequent">Frequent</option>
                  </select>
                </div>
              </section>

              <button
                type="submit"
                className="w-full bg-[#4f8684] text-white py-3 rounded-lg font-semibold hover:bg-[#3f6b69] transition-colors flex items-center justify-center space-x-2"
              >
                <Save size={20} />
                <span>Save Profile</span>
              </button>
            </form>
          </div>
        </motion.div>
      </div>
    </div>
  );
}

export default UserProfile;