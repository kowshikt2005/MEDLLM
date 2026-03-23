"use client"

import { useState, useEffect } from "react"
import { Link, useLocation } from "react-router-dom"
import { Stethoscope, Home, MessageSquare, User, Menu, X } from "lucide-react"

function Navbar() {
  const location = useLocation()
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)

  // Handle scroll effect
  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 10)
    }
    window.addEventListener("scroll", handleScroll)
    return () => window.removeEventListener("scroll", handleScroll)
  }, [])

  const isActive = (path) => location.pathname === path

  const navLinks = [
    { path: "/", label: "Home", icon: Home },
    { path: "/chat", label: "Chat", icon: MessageSquare },
    { path: "/profile", label: "Profile", icon: User },
  ]

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled ? "bg-[#4f8684]/95 backdrop-blur-sm shadow-md py-2" : "bg-[#4f8684] py-4"
      }`}
    >
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <Link to="/" className="flex items-center space-x-3 group">
            <Stethoscope size={32} className="text-white group-hover:rotate-12 transition-transform duration-300" />
            <span className="text-2xl font-bold text-white">MedLLM</span>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-6">
            {navLinks.map((link) => (
              <Link
                key={link.path}
                to={link.path}
                className={`flex items-center space-x-2 text-white relative px-3 py-2 rounded-md transition-all duration-200 ${
                  isActive(link.path) ? "text-white bg-white/10" : "hover:bg-white/5"
                }`}
              >
                <link.icon size={20} />
                <span>{link.label}</span>
                {isActive(link.path) && (
                  <span className="absolute bottom-0 left-0 w-full h-0.5 bg-cyan-100 rounded-full" />
                )}
              </Link>
            ))}
          </div>

          {/* Mobile Menu Button */}
          <button
            className="md:hidden text-white hover:bg-white/10 p-2 rounded-md"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            aria-label={isMenuOpen ? "Close menu" : "Open menu"}
          >
            {isMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>

        {/* Mobile Navigation */}
        {isMenuOpen && (
          <div className="md:hidden pt-4 pb-6 space-y-4 animate-in slide-in-from-top duration-300">
            {navLinks.map((link) => (
              <Link
                key={link.path}
                to={link.path}
                onClick={() => setIsMenuOpen(false)}
                className={`flex items-center space-x-3 text-white p-3 rounded-md transition-all ${
                  isActive(link.path) ? "bg-white/10 text-cyan-100" : "hover:bg-white/5"
                }`}
              >
                <link.icon size={20} />
                <span className="font-medium">{link.label}</span>
              </Link>
            ))}
          </div>
        )}
      </div>
    </nav>
  )
}

export default Navbar
