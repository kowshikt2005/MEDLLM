"use client"

import { useState, useRef, useEffect } from "react"
import {
  Send,
  FileText,
  ThumbsUp,
  ThumbsDown,
  MoreHorizontal,
  Menu,
  Mic,
  Download,
  ChevronDown,
  X,
  Paperclip,
  Home,
  Square,
  Copy,
  Check,
  Pause,
  Play,
  Trash,
} from "lucide-react"
import { Link } from "react-router-dom"

// Simple tooltip implementation
const Tooltip = ({ children, content }) => {
  const [isVisible, setIsVisible] = useState(false)

  return (
    <div className="relative inline-block">
      <div onMouseEnter={() => setIsVisible(true)} onMouseLeave={() => setIsVisible(false)} className="inline-block">
        {children}
      </div>
      {isVisible && (
        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 bg-gray-800 text-white text-xs rounded z-50 whitespace-nowrap">
          {content}
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-gray-800"></div>
        </div>
      )}
    </div>
  )
}

function ChatView() {
  const currentDate = new Date().toLocaleString()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [messages, setMessages] = useState([
    {
      sender: "Medicare Assistant",
      text: "Hello, I am a Medicare assistance agent. How may I help you with your healthcare needs today?",
      date: currentDate,
    },
  ])
  const [inputText, setInputText] = useState("")
  const [selectedChatId, setSelectedChatId] = useState(null) // Track selected chat
  const [isRecording, setIsRecording] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const [audioBlob, setAudioBlob] = useState(null)
  const [recordingTime, setRecordingTime] = useState(0)
  const [audioLevels, setAudioLevels] = useState([0.1, 0.2, 0.1, 0.3, 0.2, 0.1])
  const [copiedMessageIndex, setCopiedMessageIndex] = useState(null)

  const dropdownRef = useRef(null)
  const chatContainerRef = useRef(null)
  const fileInputRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])
  const animationFrameRef = useRef(null)
  const audioContextRef = useRef(null)
  const analyserRef = useRef(null)
  const micStreamRef = useRef(null)
  const timerRef = useRef(null)

  // Sample previous chats with message history
  const previousChats = [
    {
      id: 1,
      title: "Medicare Part A Coverage",
      date: "Apr 23, 2025",
      messages: [
        {
          sender: "User",
          text: "What does Medicare Part A cover?",
          date: "Apr 23, 2025, 10:00 AM",
        },
        {
          sender: "Medicare Assistant",
          text: "Medicare Part A covers hospital stays, skilled nursing facility care, hospice, and some home health care.",
          date: "Apr 23, 2025, 10:02 AM",
        },
      ],
    },
    {
      id: 2,
      title: "Prescription Plan Questions",
      date: "Apr 20, 2025",
      messages: [
        {
          sender: "User",
          text: "How do I enroll in a prescription drug plan?",
          date: "Apr 20, 2025, 2:00 PM",
        },
        {
          sender: "Medicare Assistant",
          text: "You can enroll in a Medicare Part D plan during the annual enrollment period or when you first become eligible.",
          date: "Apr 20, 2025, 2:05 PM",
        },
      ],
    },
    {
      id: 3,
      title: "Doctor Referral Process",
      date: "Apr 18, 2025",
      messages: [
        {
          sender: "User",
          text: "How do I get a referral to a specialist?",
          date: "Apr 18, 2025, 9:00 AM",
        },
        {
          sender: "Medicare Assistant",
          text: "You may need a referral from your primary care doctor depending on your Medicare plan. Contact your plan provider for details.",
          date: "Apr 18, 2025, 9:10 AM",
        },
      ],
    },
  ]

  // Get current chat title
  const getCurrentChatTitle = () => {
    if (selectedChatId) {
      const currentChat = previousChats.find((chat) => chat.id === selectedChatId)
      return currentChat ? currentChat.title : "New Conversation"
    }
    return "New Conversation"
  }

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  // Auto-scroll to the latest message
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight
    }
  }, [messages])

  // Clean up recording resources when component unmounts
  useEffect(() => {
    return () => {
      if (mediaRecorderRef.current) {
        if (mediaRecorderRef.current.state === "recording") {
          mediaRecorderRef.current.stop()
        }
      }

      if (micStreamRef.current) {
        micStreamRef.current.getTracks().forEach((track) => track.stop())
      }

      if (audioContextRef.current) {
        audioContextRef.current.close()
      }

      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
      }

      if (timerRef.current) {
        clearInterval(timerRef.current)
      }
    }
  }, [])

  // Reset copied message index after 2 seconds
  useEffect(() => {
    if (copiedMessageIndex !== null) {
      const timer = setTimeout(() => {
        setCopiedMessageIndex(null)
      }, 2000)
      return () => clearTimeout(timer)
    }
  }, [copiedMessageIndex])

  // Handle sending a message
  const handleSendMessage = () => {
    if (inputText.trim()) {
      const newMessage = {
        sender: "User",
        text: inputText,
        date: new Date().toLocaleString(),
      }
      setMessages([...messages, newMessage])
      setInputText("")

      // Update the selected chat's message history if applicable
      if (selectedChatId) {
        const updatedChats = previousChats.map((chat) =>
          chat.id === selectedChatId ? { ...chat, messages: [...chat.messages, newMessage] } : chat,
        )
        console.log("Updated chats:", updatedChats) // Replace with backend update
      }

      // Simulate assistant response (replace with API call in production)
      setTimeout(() => {
        const assistantResponse = {
          sender: "Medicare Assistant",
          text: "Thank you for your message! How can I assist you further?",
          date: new Date().toLocaleString(),
        }
        setMessages((prev) => [...prev, assistantResponse])

        if (selectedChatId) {
          const updatedChats = previousChats.map((chat) =>
            chat.id === selectedChatId ? { ...chat, messages: [...chat.messages, assistantResponse] } : chat,
          )
          console.log("Updated chats with assistant response:", updatedChats)
        }
      }, 1000)
    }
  }

  // Handle file attachment
  const handleAttachment = () => {
    fileInputRef.current.click()
  }

  const handleFileChange = (e) => {
    const files = e.target.files
    if (files.length > 0) {
      console.log("Files selected:", files)
      // Handle file upload logic here
      alert(`File "${files[0].name}" selected. Upload functionality will be implemented.`)
    }
  }

  // Handle feedback (e.g., thumbs up/down)
  const handleFeedback = (type, messageIndex) => {
    console.log(`Feedback for message ${messageIndex}: ${type}`)
    // Implement API call for feedback
  }

  // Handle key press for sending message
  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  // Handle selecting a previous chat
  const handleSelectChat = (chatId) => {
    const selectedChat = previousChats.find((chat) => chat.id === chatId)
    if (selectedChat) {
      setMessages(selectedChat.messages)
      setSelectedChatId(chatId)
      setSidebarOpen(false) // Close sidebar on mobile after selection
    }
  }

  // Toggle sidebar visibility
  const toggleSidebar = () => {
    setSidebarOpen((prev) => !prev)
    console.log("Sidebar toggled, new value:", !sidebarOpen)
  }

  // Copy message text to clipboard
  const copyMessageText = (text, index) => {
    navigator.clipboard.writeText(text).then(
      () => {
        setCopiedMessageIndex(index)
        console.log("Message copied to clipboard")
      },
      (err) => {
        console.error("Could not copy text: ", err)
      },
    )
  }

  // Start recording audio
  const startRecording = async () => {
    try {
      // Reset state
      audioChunksRef.current = []
      setRecordingTime(0)
      setIsPaused(false)

      // Get microphone access
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      micStreamRef.current = stream

      // Set up audio context for visualization
      audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)()
      analyserRef.current = audioContextRef.current.createAnalyser()
      const source = audioContextRef.current.createMediaStreamSource(stream)
      source.connect(analyserRef.current)
      analyserRef.current.fftSize = 32

      // Create media recorder
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder

      // Handle data available event
      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data)
        }
      }

      // Handle recording stop event
      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" })
        setAudioBlob(audioBlob)

        // Here you would typically send the audio to a speech-to-text service
        console.log("Recording stopped, audio blob created:", audioBlob)

        // Simulate processing the audio and getting a response
        setInputText("I need information about Medicare coverage for prescription medications.")

        // Clean up
        if (micStreamRef.current) {
          micStreamRef.current.getTracks().forEach((track) => track.stop())
        }

        if (animationFrameRef.current) {
          cancelAnimationFrame(animationFrameRef.current)
        }

        if (timerRef.current) {
          clearInterval(timerRef.current)
        }
      }

      // Start recording
      mediaRecorder.start(100)
      setIsRecording(true)

      // Start visualization
      updateAudioVisualization()

      // Start timer
      timerRef.current = setInterval(() => {
        setRecordingTime((prev) => prev + 1)
      }, 1000)
    } catch (error) {
      console.error("Error starting recording:", error)
      alert("Could not access microphone. Please check your permissions.")
    }
  }

  // Stop recording audio
  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }
  }

  // Pause recording
  const pauseRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.pause()
      setIsPaused(true)

      // Pause timer
      if (timerRef.current) {
        clearInterval(timerRef.current)
      }
    }
  }

  // Resume recording
  const resumeRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "paused") {
      mediaRecorderRef.current.resume()
      setIsPaused(false)

      // Resume timer
      timerRef.current = setInterval(() => {
        setRecordingTime((prev) => prev + 1)
      }, 1000)
    }
  }

  // Toggle recording state
  const toggleRecording = () => {
    if (isRecording) {
      stopRecording()
    } else {
      startRecording()
    }
  }

  // Cancel recording
  const cancelRecording = () => {
    if (mediaRecorderRef.current) {
      if (mediaRecorderRef.current.state === "recording" || mediaRecorderRef.current.state === "paused") {
        mediaRecorderRef.current.stop()
      }

      // Clear audio chunks
      audioChunksRef.current = []
      setAudioBlob(null)
      setIsRecording(false)

      // Clean up
      if (micStreamRef.current) {
        micStreamRef.current.getTracks().forEach((track) => track.stop())
      }

      if (timerRef.current) {
        clearInterval(timerRef.current)
      }

      console.log("Recording canceled")
    }
  }

  // Update audio visualization
  const updateAudioVisualization = () => {
    if (!analyserRef.current || !isRecording || isPaused) return

    const bufferLength = analyserRef.current.frequencyBinCount
    const dataArray = new Uint8Array(bufferLength)
    analyserRef.current.getByteFrequencyData(dataArray)

    // Calculate audio levels from frequency data
    const levels = []
    const step = Math.floor(bufferLength / 6) // We want 6 bars

    for (let i = 0; i < 6; i++) {
      let sum = 0
      for (let j = 0; j < step; j++) {
        const index = i * step + j
        if (index < bufferLength) {
          sum += dataArray[index]
        }
      }
      // Normalize between 0.1 and 1
      const level = Math.max(0.1, Math.min(1, sum / (step * 255)))
      levels.push(level)
    }

    setAudioLevels(levels)
    animationFrameRef.current = requestAnimationFrame(updateAudioVisualization)
  }

  // Format recording time
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs < 10 ? "0" : ""}${secs}`
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Chat Interface Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar for previous chats - ONLY visible when sidebarOpen is true */}
        {sidebarOpen && (
          <div className="w-64 bg-white border-r border-gray-200 overflow-y-auto fixed h-full z-30 md:w-1/4 md:static shadow-lg">
            <div className="p-4 border-b border-gray-200 bg-teal-50">
              <h3 className="font-semibold text-teal-800 text-lg">Your Conversations</h3>
            </div>
            <div className="p-4">
              {previousChats.map((chat) => (
                <div
                  key={chat.id}
                  className={`mb-3 p-3 rounded-lg cursor-pointer transition-all duration-200 ${
                    selectedChatId === chat.id
                      ? "bg-teal-100 border-l-4 border-teal-600 shadow-sm font-medium"
                      : "hover:bg-gray-100 border-l-4 border-transparent"
                  }`}
                  onClick={() => handleSelectChat(chat.id)}
                >
                  <div className="font-medium text-gray-800">{chat.title}</div>
                  <div className="text-sm text-gray-500 mt-1">{chat.date}</div>
                </div>
              ))}
              <button
                className="w-full mt-4 p-3 bg-teal-700 text-white rounded-lg hover:bg-teal-800 transition-colors"
                onClick={() => {
                  setSelectedChatId(null)
                  setMessages([
                    {
                      sender: "Medicare Assistant",
                      text: "Hello, I am a Medicare assistance agent. How may I help you with your healthcare needs today?",
                      date: new Date().toLocaleString(),
                    },
                  ])
                  setSidebarOpen(false)
                }}
              >
                Start New Chat
              </button>
            </div>
          </div>
        )}

        {/* Mobile backdrop for sidebar - only shows when sidebar is open */}
        {sidebarOpen && (
          <div className="fixed inset-0 bg-black bg-opacity-50 z-20 md:hidden" onClick={toggleSidebar}></div>
        )}

        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Chat header */}
          <div className="bg-gradient-to-r from-teal-800 to-teal-700 text-white px-4 py-3 flex items-center justify-between shadow-md">
            <div className="flex items-center">
              <button
                aria-label="Toggle sidebar"
                aria-expanded={sidebarOpen}
                onClick={toggleSidebar}
                className="hover:bg-teal-700 rounded-full p-2 transition-colors mr-3"
              >
                {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
              </button>
              <span className="font-medium text-lg">{getCurrentChatTitle()}</span>
            </div>
            <div className="flex items-center gap-4">
              <Link
                to="/"
                className="flex items-center bg-teal-700 hover:bg-teal-600 px-3 py-1 rounded-md transition-colors"
              >
                <Home size={16} className="mr-1" />
                <span className="text-sm">Home</span>
              </Link>
              {/* Profile Dropdown */}
              <div className="relative" ref={dropdownRef}>
                <button
                  aria-label="Toggle profile dropdown"
                  onClick={() => setDropdownOpen(!dropdownOpen)}
                  className="flex items-center gap-2 focus:outline-none hover:bg-teal-700 p-2 rounded-full"
                >
                  <ChevronDown size={16} />
                </button>
                {dropdownOpen && (
                  <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg z-10">
                    <Link to="/profile" className="block px-4 py-2 text-gray-700 hover:bg-gray-100">
                      Profile
                    </Link>
                    <button
                      onClick={() => {
                        console.log("Logout clicked")
                        localStorage.removeItem("authToken")
                        window.location.href = "/login"
                      }}
                      className="w-full text-left px-4 py-2 text-gray-700 hover:bg-gray-100"
                    >
                      Logout
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Chat messages */}
          <div ref={chatContainerRef} className="flex-1 overflow-y-auto p-4 bg-gray-50">
            {messages.map((message, index) => (
              <div key={index} className="flex gap-3 mb-6 opacity-100 transition-opacity duration-300 ease-in">
                <div
                  className={`${
                    message.sender === "User"
                      ? "bg-gradient-to-br from-blue-600 to-blue-700"
                      : "bg-gradient-to-br from-teal-700 to-teal-800"
                  } rounded-full w-10 h-10 flex items-center justify-center flex-shrink-0 shadow-sm`}
                >
                  <span className="text-white font-medium">{message.sender === "User" ? "U" : "M"}</span>
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{message.sender}</span>
                    <span className="text-gray-500 text-sm">{message.date}</span>
                  </div>
                  <div
                    className={`mt-2 ${
                      message.sender === "User"
                        ? "bg-blue-100 border-blue-200 text-blue-900"
                        : "bg-white border-gray-200 text-gray-800"
                    } border rounded-lg p-4 shadow-sm relative group`}
                  >
                    <p>{message.text}</p>

                    {/* Copy button - visible on hover */}
                    <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Tooltip content={copiedMessageIndex === index ? "Copied!" : "Copy message"}>
                        <button
                          onClick={() => copyMessageText(message.text, index)}
                          className="p-1 rounded-md bg-gray-100 hover:bg-gray-200 text-gray-600"
                          aria-label="Copy message"
                        >
                          {copiedMessageIndex === index ? <Check size={14} /> : <Copy size={14} />}
                        </button>
                      </Tooltip>
                    </div>
                  </div>
                  {message.sender !== "User" && (
                    <div className="flex gap-2 mt-2">
                      <button
                        aria-label="View details"
                        className="text-gray-500 hover:text-gray-700 p-1 transition-colors"
                        onClick={() => console.log("View details clicked")}
                      >
                        <FileText size={18} />
                      </button>
                      <button
                        aria-label="Like message"
                        className="text-gray-500 hover:text-green-600 p-1 transition-colors"
                        onClick={() => handleFeedback("positive", index)}
                      >
                        <ThumbsUp size={18} />
                      </button>
                      <button
                        aria-label="Dislike message"
                        className="text-gray-500 hover:text-red-600 p-1 transition-colors"
                        onClick={() => handleFeedback("negative", index)}
                      >
                        <ThumbsDown size={18} />
                      </button>
                      <button
                        aria-label="More options"
                        className="text-gray-500 hover:text-gray-700 p-1 transition-colors"
                        onClick={() => console.log("More options clicked")}
                      >
                        <MoreHorizontal size={18} />
                      </button>
                      <button
                        aria-label="Download message"
                        className="text-gray-500 hover:text-blue-600 p-1 transition-colors"
                        onClick={() => console.log("Download clicked")}
                      >
                        <Download size={18} />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* User Input Area */}
          <div className="border-t border-gray-200 p-4 bg-white shadow-inner">
            {isRecording ? (
              <div className="flex flex-col items-center bg-gradient-to-b from-teal-50 to-white p-4 rounded-lg border border-teal-200 shadow-sm">
                {/* Voice Recording Animation */}
                <div className="flex items-end justify-center gap-1 h-20 mb-4 bg-teal-50 p-3 rounded-lg w-full">
                  {audioLevels.map((level, index) => (
                    <div
                      key={index}
                      className="w-3 bg-teal-600 rounded-full transition-all duration-100 ease-out audio-bar"
                      style={{
                        height: `${level * 100}%`,
                        opacity: 0.7 + level * 0.3,
                        animationPlayState: isPaused ? "paused" : "running",
                        "--index": index,
                      }}
                    ></div>
                  ))}
                </div>

                {/* Recording Status */}
                <div className="mb-3 flex items-center">
                  <span
                    className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                      isPaused ? "bg-amber-100 text-amber-800" : "bg-red-100 text-red-800"
                    } border-none`}
                  >
                    {isPaused ? "Paused" : "Recording"} {isPaused ? "" : "..."}
                  </span>
                  <span className="ml-3 text-gray-700 font-medium">{formatTime(recordingTime)}</span>
                </div>

                {/* Recording Controls */}
                <div className="flex items-center gap-3">
                  {isPaused ? (
                    <button
                      onClick={resumeRecording}
                      className="inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none bg-teal-100 hover:bg-teal-200 border border-teal-300 text-teal-700 h-10 w-10"
                      aria-label="Resume recording"
                    >
                      <Play size={18} />
                    </button>
                  ) : (
                    <button
                      onClick={pauseRecording}
                      className="inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none bg-amber-100 hover:bg-amber-200 border border-amber-300 text-amber-700 h-10 w-10"
                      aria-label="Pause recording"
                    >
                      <Pause size={18} />
                    </button>
                  )}

                  <button
                    onClick={stopRecording}
                    className="inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none bg-teal-700 hover:bg-teal-800 text-white h-10 w-10"
                    aria-label="Stop recording"
                  >
                    <Square size={18} />
                  </button>

                  <button
                    onClick={cancelRecording}
                    className="inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none bg-red-100 hover:bg-red-200 border border-red-300 text-red-700 h-10 w-10"
                    aria-label="Cancel recording"
                  >
                    <Trash size={18} />
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-2 bg-white p-2 rounded-lg border border-gray-200 shadow-sm">
                <textarea
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder="Type your message..."
                  className="flex-1 p-3 bg-gray-50 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent resize-none"
                  rows="2"
                />
                <div className="flex flex-col gap-2">
                  <input type="file" ref={fileInputRef} onChange={handleFileChange} className="hidden" multiple />
                  <Tooltip content="Attach file">
                    <button
                      onClick={handleAttachment}
                      className="inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none bg-gray-50 hover:bg-gray-100 border border-gray-200 text-gray-700 h-10 w-10"
                      aria-label="Attach file"
                    >
                      <Paperclip size={18} />
                    </button>
                  </Tooltip>

                  <Tooltip content="Record voice message">
                    <button
                      onClick={toggleRecording}
                      className="inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none bg-teal-50 hover:bg-teal-100 border border-teal-200 text-teal-700 h-10 w-10"
                      aria-label="Record voice message"
                    >
                      <Mic size={18} />
                    </button>
                  </Tooltip>
                </div>
                <button
                  onClick={handleSendMessage}
                  disabled={!inputText.trim()}
                  className={`inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none h-full ${
                    inputText.trim()
                      ? "bg-teal-700 hover:bg-teal-600 text-white"
                      : "bg-gray-200 text-gray-400 cursor-not-allowed"
                  }`}
                  aria-label="Send message"
                >
                  <Send size={18} />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default ChatView
