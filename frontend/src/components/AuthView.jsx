"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Stethoscope, User } from "lucide-react"

// Simple utility to join class names, replacing cn
const classNames = (...classes) => classes.filter(Boolean).join(" ")

export default function AuthView({ onLogin = () => {} }) {
  const [activeTab, setActiveTab] = useState("login")
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    fullName: "",
    phoneNumber: "",
    confirmPassword: "",
  })
  const [errors, setErrors] = useState({})
  const [touched, setTouched] = useState({})

  const validateField = (name, value) => {
    let error = ""

    switch (name) {
      case "email":
        if (!value) {
          error = "Email is required"
        } else if (!/\S+@\S+\.\S+/.test(value)) {
          error = "Email is invalid"
        }
        break
      case "password":
        if (!value) {
          error = "Password is required"
        } else if (value.length < 6) {
          error = "Password must be at least 6 characters"
        }
        break
      case "fullName":
        if (!value && activeTab === "signup") {
          error = "Full name is required"
        }
        break
      case "confirmPassword":
        if (!value && activeTab === "signup") {
          error = "Please confirm your password"
        } else if (value !== formData.password) {
          error = "Passwords do not match"
        }
        break
      case "phoneNumber":
        if (activeTab === "signup" && value && !/^\d{10}$/.test(value.replace(/\D/g, ""))) {
          error = "Please enter a valid phone number"
        }
        break
      default:
        break
    }

    return error
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))

    setTouched((prev) => ({ ...prev, [name]: true }))
    const error = validateField(name, value)
    setErrors((prev) => ({ ...prev, [name]: error }))
  }

  const handleBlur = (e) => {
    const { name, value } = e.target
    setTouched((prev) => ({ ...prev, [name]: true }))
    const error = validateField(name, value)
    setErrors((prev) => ({ ...prev, [name]: error }))
  }

  const validateForm = () => {
    const newErrors = {}
    let isValid = true

    // Mark all fields as touched
    const newTouched = {}

    if (activeTab === "login") {
      ;["email", "password"].forEach((field) => {
        newTouched[field] = true
        const error = validateField(field, formData[field])
        if (error) {
          isValid = false
          newErrors[field] = error
        }
      })
    } else {
      ;["email", "password", "fullName", "confirmPassword", "phoneNumber"].forEach((field) => {
        newTouched[field] = true
        const error = validateField(field, formData[field])
        if (error) {
          isValid = false
          newErrors[field] = error
        }
      })
    }

    setTouched(newTouched)
    setErrors(newErrors)
    return isValid
  }

  const handleSubmit = (e) => {
    e.preventDefault()

    if (validateForm()) {
      console.log("Form submitted successfully", formData)
      onLogin()
    } else {
      console.log("Form has errors", errors)
    }
  }

  const switchTab = (tab) => {
    setActiveTab(tab)
    setErrors({})
    setTouched({})
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-cyan-50 p-4">
      <div className="w-full max-w-4xl bg-white rounded-2xl shadow-xl overflow-hidden">
        <div className="flex flex-col md:flex-row">
          {/* Left Panel */}
          <AnimatePresence initial={false} mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="w-full md:w-1/2"
            >
              {activeTab === "login" ? (
                <div className="bg-[#4f8684] p-12 text-white h-full flex flex-col justify-center">
                  <div className="w-16 h-16 rounded-full bg-white/10 flex items-center justify-center mb-8">
                    <Stethoscope className="text-white" size={32} />
                  </div>
                  <h2 className="text-4xl font-bold mb-4">Welcome to</h2>
                  <h2 className="text-4xl font-bold mb-6">MediClient</h2>
                  <p className="text-lg">
                    Your comprehensive healthcare management solution. Experience seamless medical care coordination.
                  </p>
                </div>
              ) : (
                <div className="bg-white p-12 h-full">
                  <h2 className="text-3xl font-bold mb-4">Create Account</h2>
                  <p className="text-gray-600 mb-8">Join MediClient and start managing your healthcare journey</p>

                  <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="space-y-1">
                      <label htmlFor="fullName" className="text-sm font-medium">
                        Full Name
                      </label>
                      <input
                        type="text"
                        id="fullName"
                        name="fullName"
                        value={formData.fullName}
                        onChange={handleChange}
                        onBlur={handleBlur}
                        className={classNames(
                          "w-full px-4 py-3 rounded-lg border focus:outline-none focus:ring-2 focus:ring-[#4f8684]",
                          errors.fullName && touched.fullName ? "border-red-500" : "border-gray-300"
                        )}
                      />
                      {errors.fullName && touched.fullName && <p className="text-red-500 text-sm">{errors.fullName}</p>}
                    </div>

                    <div className="space-y-1">
                      <label htmlFor="email" className="text-sm font-medium">
                        Email address
                      </label>
                      <input
                        type="email"
                        id="email"
                        name="email"
                        value={formData.email}
                        onChange={handleChange}
                        onBlur={handleBlur}
                        className={classNames(
                          "w-full px-4 py-3 rounded-lg border focus:outline-none focus:ring-2 focus:ring-[#4f8684]",
                          errors.email && touched.email ? "border-red-500" : "border-gray-300"
                        )}
                      />
                      {errors.email && touched.email && <p className="text-red-500 text-sm">{errors.email}</p>}
                    </div>

                    <div className="space-y-1">
                      <label htmlFor="phoneNumber" className="text-sm font-medium">
                        Phone number
                      </label>
                      <input
                        type="tel"
                        id="phoneNumber"
                        name="phoneNumber"
                        value={formData.phoneNumber}
                        onChange={handleChange}
                        onBlur={handleBlur}
                        className={classNames(
                          "w-full px-4 py-3 rounded-lg border focus:outline-none focus:ring-2 focus:ring-[#4f8684]",
                          errors.phoneNumber && touched.phoneNumber ? "border-red-500" : "border-gray-300"
                        )}
                      />
                      {errors.phoneNumber && touched.phoneNumber && (
                        <p className="text-red-500 text-sm">{errors.phoneNumber}</p>
                      )}
                    </div>

                    <div className="space-y-1">
                      <label htmlFor="password" className="text-sm font-medium">
                        Password
                      </label>
                      <input
                        type="password"
                        id="password"
                        name="password"
                        value={formData.password}
                        onChange={handleChange}
                        onBlur={handleBlur}
                        className={classNames(
                          "w-full px-4 py-3 rounded-lg border focus:outline-none focus:ring-2 focus:ring-[#4f8684]",
                          errors.password && touched.password ? "border-red-500" : "border-gray-300"
                        )}
                      />
                      {errors.password && touched.password && <p className="text-red-500 text-sm">{errors.password}</p>}
                    </div>

                    <div className="space-y-1">
                      <label htmlFor="confirmPassword" className="text-sm font-medium">
                        Confirm Password
                      </label>
                      <input
                        type="password"
                        id="confirmPassword"
                        name="confirmPassword"
                        value={formData.confirmPassword}
                        onChange={handleChange}
                        onBlur={handleBlur}
                        className={classNames(
                          "w-full px-4 py-3 rounded-lg border focus:outline-none focus:ring-2 focus:ring-[#4f8684]",
                          errors.confirmPassword && touched.confirmPassword ? "border-red-500" : "border-gray-300"
                        )}
                      />
                      {errors.confirmPassword && touched.confirmPassword && (
                        <p className="text-red-500 text-sm">{errors.confirmPassword}</p>
                      )}
                    </div>

                    <div className="flex space-x-4 mt-6">
                      <button
                        type="button"
                        onClick={() => switchTab("login")}
                        className="flex-1 py-3 border border-[#4f8684] text-[#4f8684] font-medium rounded-lg hover:bg-gray-50 transition-colors"
                      >
                        LOG IN
                      </button>
                      <button
                        type="submit"
                        className="flex-1 bg-[#0f1c1b] text-white py-3 rounded-lg font-medium hover:bg-[#1a2e2d] transition-colors"
                      >
                        SIGN UP
                      </button>
                    </div>
                  </form>
                </div>
              )}
            </motion.div>
          </AnimatePresence>

          {/* Right Panel */}
          <AnimatePresence initial={false} mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="w-full md:w-1/2"
            >
              {activeTab === "login" ? (
                <div className="bg-white p-12 h-full">
                  <h2 className="text-3xl font-bold mb-4">Log in</h2>
                  <p className="text-gray-600 mb-8">Enter your credentials to access your account</p>

                  <div className="flex mb-8">
                    <button
                      onClick={() => switchTab("login")}
                      className={classNames(
                        "flex-1 py-2 font-medium text-center border-b-2",
                        activeTab === "login" ? "border-[#4f8684] text-[#4f8684]" : "border-gray-200 text-gray-500"
                      )}
                    >
                      LOG IN
                    </button>
                    <button
                      onClick={() => switchTab("signup")}
                      className={classNames(
                        "flex-1 py-2 font-medium text-center border-b-2",
                        activeTab === "signup" ? "border-[#4f8684] text-[#4f8684]" : "border-gray-200 text-gray-500"
                      )}
                    >
                      SIGN UP
                    </button>
                  </div>

                  <form onSubmit={handleSubmit} className="space-y-6">
                    <div className="space-y-1">
                      <label htmlFor="loginEmail" className="text-sm font-medium">
                        Email address or phone number
                      </label>
                      <input
                        type="email"
                        id="loginEmail"
                        name="email"
                        value={formData.email}
                        onChange={handleChange}
                        onBlur={handleBlur}
                        placeholder="example@gmail.com"
                        className={classNames(
                          "w-full px-4 py-3 rounded-lg border focus:outline-none focus:ring-2 focus:ring-[#4f8684]",
                          errors.email && touched.email ? "border-red-500" : "border-gray-300"
                        )}
                      />
                      {errors.email && touched.email && <p className="text-red-500 text-sm">{errors.email}</p>}
                    </div>

                    <div className="space-y-1">
                      <div className="flex justify-between items-center">
                        <label htmlFor="loginPassword" className="text-sm font-medium">
                          Password
                        </label>
                        <a href="#" className="text-sm text-[#4f8684] hover:underline">
                          Forgot password?
                        </a>
                      </div>
                      <input
                        type="password"
                        id="loginPassword"
                        name="password"
                        value={formData.password}
                        onChange={handleChange}
                        onBlur={handleBlur}
                        placeholder="••••••••"
                        className={classNames(
                          "w-full px-4 py-3 rounded-lg border focus:outline-none focus:ring-2 focus:ring-[#4f8684]",
                          errors.password && touched.password ? "border-red-500" : "border-gray-300"
                        )}
                      />
                      {errors.password && touched.password && <p className="text-red-500 text-sm">{errors.password}</p>}
                    </div>

                    <button
                      type="submit"
                      className="w-full bg-[#0f1c1b] text-white py-3 rounded-lg font-medium hover:bg-[#1a2e2d] transition-colors"
                    >
                      LOG IN
                    </button>
                  </form>
                </div>
              ) : (
                <div className="bg-[#4f8684] p-12 text-white h-full flex flex-col justify-center">
                  <div className="w-16 h-16 rounded-full bg-white/10 flex items-center justify-center mb-8">
                    <User className="text-white" size={32} />
                  </div>
                  <h2 className="text-4xl font-bold mb-4">Join</h2>
                  <h2 className="text-4xl font-bold mb-6">MediClient</h2>
                  <p className="text-lg">
                    Start your journey to better healthcare management with MediClient's comprehensive platform.
                  </p>
                </div>
              )}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}