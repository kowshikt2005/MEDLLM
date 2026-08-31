"use client"

import { useState } from "react"
import { motion, useScroll, useTransform } from "framer-motion"
import { Link } from "react-router-dom"
import {
  Brain,
  Shield,
  Activity,
  ChevronDown,
  FileText,
  Microscope,
  Stethoscope,
  HeartPulse,
  Pill,
  Clock,
  CheckCircle2,
  ArrowRight,
} from "lucide-react"
import Navbar from "./Navbar"

function HomePage() {
  const { scrollY } = useScroll()
  const y = useTransform(scrollY, [0, 300], [0, -50])
  const opacity = useTransform(scrollY, [0, 300], [1, 0])
  const [profileUpdated, setProfileUpdated] = useState(false)

  // Parallax effect for background elements
  const bgParallax1 = useTransform(scrollY, [0, 1000], [0, -150])
  const bgParallax2 = useTransform(scrollY, [0, 1000], [0, -100])


  const features = [
    {
      icon: Brain,
      title: "Local model experimentation",
      description:
        "Choose an installed Ollama completion model and check its availability before starting normal chat.",
    },
    {
      icon: Shield,
      title: "Multimodal input pipeline",
      description:
        "The project accepts PDF, DOCX, text, images with OCR, and browser-recorded audio for local processing.",
    },
    {
      icon: Activity,
      title: "Grounded normal mode",
      description:
        "Normal chat uses retrieved excerpts only and abstains when the current sources do not support a question.",
    },
    {
      icon: FileText,
      title: "Visible source links",
      description:
        "Retrieved references show their title, source type, relevance signal, and direct source link when available.",
    },
    {
      icon: Microscope,
      title: "Pinned starter corpus",
      description:
        "Three reviewed CDC source cards for diabetes and high blood pressure can be verified and rebuilt locally.",
    },
    {
      icon: Stethoscope,
      title: "Explicit limits",
      description:
        "The project does not provide diagnoses, treatment plans, medical accuracy scores, or a currentness guarantee.",
    },
  ]

  const workflowSteps = [
    {
      icon: FileText,
      title: "Choose a question or document",
      description: "Use the small curated source set or attach a document for local retrieval.",
    },
    {
      icon: Brain,
      title: "Select a local model",
      description: "Normal mode checks the selected Ollama model before it starts generation.",
    },
    {
      icon: HeartPulse,
      title: "Retrieve excerpts",
      description: "Chroma finds relevant chunks and passes their source metadata to the answer flow.",
    },
    {
      icon: Pill,
      title: "Read supported content",
      description: "Answers are limited to retrieved evidence and show the retrieved references below the response.",
    },
    {
      icon: Clock,
      title: "Abstain on gaps",
      description: "If no source supports a question, normal mode says so instead of filling the gap from general knowledge.",
    },
  ]


  const stats = [
    { value: "3", label: "Reviewed CDC source cards" },
    { value: "6", label: "Initial curated index chunks" },
    { value: "Local", label: "Ollama normal-chat runtime" },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-b from-cyan-50 to-white overflow-hidden">
      <Navbar />

      <main>
        {/* Hero Section with animated background elements */}
        <section className="relative h-screen flex items-center justify-center overflow-hidden">
          {/* Animated background elements */}
          <motion.div
            style={{ y: bgParallax1 }}
            className="absolute top-20 right-10 w-64 h-64 rounded-full bg-teal-100 opacity-30 blur-3xl"
          />
          <motion.div
            style={{ y: bgParallax2 }}
            className="absolute bottom-40 left-20 w-80 h-80 rounded-full bg-cyan-100 opacity-40 blur-3xl"
          />

          <motion.div style={{ y, opacity }} className="container mx-auto px-4 text-center z-10">
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.8 }}
              className="inline-block mb-6 px-4 py-1 bg-teal-100 text-teal-800 rounded-full text-sm font-medium"
            >
              Powered by Retrieval-Augmented Generation
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8 }}
              className="text-5xl md:text-7xl font-bold text-gray-900 mb-6"
            >
              Source-Grounded
              <span className="text-[#4f8684] block mt-2">Local RAG Exploration</span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.2 }}
              className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto"
            >
              Explore a local model, retrieval, and document-processing workflow. Normal mode uses only retrieved sources and states when the current corpus cannot support an answer.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.4 }}
              className="flex flex-col sm:flex-row justify-center gap-4"
            >
              <Link
                to="/profile"
                className="bg-[#4f8684] text-white px-8 py-3 rounded-lg font-semibold hover:bg-[#3f6b69] transition-all transform hover:scale-105 shadow-lg hover:shadow-xl flex items-center justify-center"
                onClick={() => setTimeout(() => setProfileUpdated(true), 500)}
              >
                Complete Your Profile <ArrowRight className="ml-2 h-5 w-5" />
              </Link>
              <Link
                to="/chat"
                className="bg-white text-[#4f8684] border border-[#4f8684] px-8 py-3 rounded-lg font-semibold hover:bg-gray-50 transition-all transform hover:scale-105 shadow-md hover:shadow-lg"
              >
                See How It Works
              </Link>
            </motion.div>

            {profileUpdated && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-6 bg-green-100 text-green-800 px-4 py-2 rounded-lg inline-flex items-center"
              >
                <CheckCircle2 className="h-5 w-5 mr-2" /> Profile updated successfully!
              </motion.div>
            )}

            {/* Floating badges */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 1, duration: 1 }}
              className="flex flex-wrap justify-center gap-4 mt-12"
            >
              <div className="bg-white/80 backdrop-blur-sm px-4 py-2 rounded-full shadow-md text-sm text-gray-700 flex items-center">
                <CheckCircle2 className="h-4 w-4 mr-2 text-teal-600" /> Source-grounded normal mode
              </div>
              <div className="bg-white/80 backdrop-blur-sm px-4 py-2 rounded-full shadow-md text-sm text-gray-700 flex items-center">
                <Brain className="h-4 w-4 mr-2 text-teal-600" /> AI-Powered
              </div>
            </motion.div>
          </motion.div>

          <motion.div
            animate={{ y: [0, 10, 0] }}
            transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}
            className="absolute bottom-10 left-1/2 transform -translate-x-1/2 z-10"
          >
            <ChevronDown className="text-gray-500" size={32} />
          </motion.div>
        </section>

        {/* Stats Section */}
        <section className="py-16 bg-white">
          <div className="container mx-auto px-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
              {stats.map((stat, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: index * 0.1 }}
                  viewport={{ once: true }}
                  className="text-center"
                >
                  <h3 className="text-4xl font-bold text-[#4f8684] mb-2">{stat.value}</h3>
                  <p className="text-gray-600">{stat.label}</p>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section className="py-20 bg-gradient-to-b from-white to-cyan-50">
          <div className="container mx-auto px-4">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8 }}
              viewport={{ once: true }}
              className="text-center mb-16"
            >
              <div className="inline-block px-3 py-1 bg-teal-100 text-teal-800 rounded-full text-sm font-medium mb-4">
                Prototype capabilities
              </div>
              <h2 className="text-4xl font-bold text-gray-900 mb-4">What this project demonstrates</h2>
              <p className="text-xl text-gray-600 max-w-3xl mx-auto">
                A local, inspectable workflow for model selection, retrieval, source attribution, and abstention.
              </p>
            </motion.div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              {features.map((feature, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.8, delay: index * 0.1 }}
                  viewport={{ once: true }}
                  whileHover={{ y: -5, transition: { duration: 0.2 } }}
                  className="bg-white p-8 rounded-2xl shadow-lg hover:shadow-xl transition-all border border-gray-100"
                >
                  <div className="w-16 h-16 bg-cyan-100 rounded-2xl flex items-center justify-center mb-6">
                    <feature.icon className="text-[#4f8684]" size={32} />
                  </div>
                  <h3 className="text-2xl font-semibold text-gray-900 mb-4">{feature.title}</h3>
                  <p className="text-gray-600 leading-relaxed">{feature.description}</p>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* How It Works Section */}
        <section className="py-20 bg-white">
          <div className="container mx-auto px-4">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8 }}
              viewport={{ once: true }}
              className="text-center mb-16"
            >
              <div className="inline-block px-3 py-1 bg-teal-100 text-teal-800 rounded-full text-sm font-medium mb-4">
                Simple Process
              </div>
              <h2 className="text-4xl font-bold text-gray-900 mb-4">How MedLLM Works</h2>
              <p className="text-xl text-gray-600 max-w-3xl mx-auto">
                The normal path checks a local model, retrieves source excerpts, and either answers from them or abstains.
              </p>
            </motion.div>

            <div className="relative">
              {/* Connecting line */}
              <div className="absolute top-1/2 left-0 right-0 h-1 bg-teal-100 -translate-y-1/2 hidden md:block"></div>

              <div className="grid grid-cols-1 md:grid-cols-5 gap-8">
                {workflowSteps.map((step, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, delay: index * 0.2 }}
                    viewport={{ once: true }}
                    className="flex flex-col items-center text-center relative z-10"
                  >
                    <div className="w-20 h-20 bg-white border-4 border-teal-100 rounded-full flex items-center justify-center mb-6 shadow-lg">
                      <step.icon className="text-[#4f8684]" size={32} />
                    </div>
                    <div className="bg-white p-4 rounded-xl shadow-md w-full">
                      <h3 className="text-xl font-semibold text-gray-900 mb-2">{step.title}</h3>
                      <p className="text-gray-600 text-sm">{step.description}</p>
                    </div>
                    {index < workflowSteps.length - 1 && (
                      <div className="hidden md:block absolute top-10 -right-4 transform translate-x-1/2">
                        <ArrowRight className="text-teal-300" size={24} />
                      </div>
                    )}
                  </motion.div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Technology Section */}
        <section className="py-20 bg-white">
          <div className="container mx-auto px-4">
            <div className="grid md:grid-cols-2 gap-12 items-center">
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.8 }}
                viewport={{ once: true }}
              >
                <div className="inline-block px-3 py-1 bg-teal-100 text-teal-800 rounded-full text-sm font-medium mb-4">
                  Advanced Technology
                </div>
                <h2 className="text-4xl font-bold text-gray-900 mb-6">Powered by Retrieval-Augmented Generation</h2>
                <p className="text-gray-600 mb-6 leading-relaxed">
                  MedLLM combines a locally selected language model with a small, reviewable Chroma index. The normal path does not use general knowledge to fill retrieval gaps.
                </p>
                <ul className="space-y-4">
                  {[
                    "Processes PDF, DOCX, text, image-OCR, and browser-recorded audio inputs",
                    "Shows retrieved source labels and direct links where source metadata includes a URL",
                    "Uses a three-card CDC starter corpus that can be verified by SHA-256 and rebuilt locally",
                    "Returns a fixed abstention when the retrieved sources do not support the question",
                  ].map((item, index) => (
                    <li key={index} className="flex items-start">
                      <CheckCircle2 className="h-5 w-5 text-teal-600 mr-2 mt-0.5 flex-shrink-0" />
                      <span className="text-gray-700">{item}</span>
                    </li>
                  ))}
                </ul>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, x: 20 }}
                whileInView={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.8 }}
                viewport={{ once: true }}
                className="relative"
              >
                <div className="bg-gradient-to-br from-cyan-100 to-teal-100 rounded-2xl p-1">
                  <div className="bg-white rounded-xl p-6 shadow-lg">
                    <div className="flex items-center mb-4">
                      <div className="w-3 h-3 bg-red-500 rounded-full mr-2"></div>
                      <div className="w-3 h-3 bg-yellow-500 rounded-full mr-2"></div>
                      <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                    </div>
                    <div className="space-y-4">
                      <div className="bg-gray-100 rounded-lg p-3">
                        <p className="text-gray-800 font-mono text-sm">
                          <span className="text-purple-600">Question:</span> What does the available source say about
                          high blood pressure?
                        </p>
                      </div>
                      <div className="bg-teal-50 rounded-lg p-3">
                        <p className="text-gray-800 font-mono text-sm">
                          <span className="text-teal-600">MedLLM:</span> I will answer only from retrieved excerpts
                          and show the references used below this response.
                        </p>
                      </div>
                      <div className="bg-teal-50 rounded-lg p-3">
                        <p className="text-gray-800 font-mono text-sm">
                          <span className="text-teal-600">MedLLM:</span> If the retrieved sources do not support the
                          question, I will abstain rather than add unsupported information.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Decorative elements */}
                <div className="absolute -top-6 -right-6 w-20 h-20 bg-cyan-100 rounded-full opacity-50"></div>
                <div className="absolute -bottom-8 -left-8 w-24 h-24 bg-teal-100 rounded-full opacity-60"></div>
              </motion.div>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="py-20 bg-gradient-to-r from-[#4f8684] to-[#3f6b69]">
          <div className="container mx-auto px-4">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8 }}
              viewport={{ once: true }}
              className="text-center text-white max-w-3xl mx-auto"
            >
              <h2 className="text-4xl font-bold mb-6">Explore the local retrieval workflow</h2>
              <p className="text-xl mb-8">
                Choose a local model, inspect the retrieved sources, and test the grounded answer and abstention behavior.
              </p>
              <div className="flex flex-col sm:flex-row justify-center gap-4">
                <Link
                  to="/profile"
                  className="bg-white text-[#4f8684] px-8 py-4 rounded-lg font-semibold hover:bg-gray-100 transition-all inline-block transform hover:scale-105 shadow-lg"
                  onClick={() => setTimeout(() => setProfileUpdated(true), 500)}
                >
                  Complete Your Profile
                </Link>
                <Link
                  to="/chat"
                  className="bg-transparent text-white border border-white px-8 py-4 rounded-lg font-semibold hover:bg-white/10 transition-all inline-block transform hover:scale-105"
                >
                  Learn More
                </Link>
              </div>
            </motion.div>
          </div>
        </section>

        {/* FAQ Section */}
        <section className="py-20 bg-white">
          <div className="container mx-auto px-4">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8 }}
              viewport={{ once: true }}
              className="text-center mb-16"
            >
              <div className="inline-block px-3 py-1 bg-teal-100 text-teal-800 rounded-full text-sm font-medium mb-4">
                Common Questions
              </div>
              <h2 className="text-4xl font-bold text-gray-900 mb-4">Frequently Asked Questions</h2>
              <p className="text-xl text-gray-600 max-w-3xl mx-auto">
                How the local retrieval workflow behaves and where its evidence boundary stops
              </p>
            </motion.div>

            <div className="max-w-3xl mx-auto">
              {[
                {
                  question: "What happens when the sources do not cover a question?",
                  answer:
                    "Normal mode returns an abstention instead of generating an answer when no retrieved source supports the question. This is a product behavior, not evidence of medical reliability.",
                },
                {
                  question: "How does Retrieval-Augmented Generation work?",
                  answer:
                    "RAG retrieves relevant chunks from the local Chroma index and gives those excerpts to the selected local model. Normal mode is instructed to stay within those excerpts and displays the retrieved references.",
                },
                {
                  question: "Can MedLLM replace my doctor?",
                  answer:
                    "No. It is a software project for exploring local retrieval workflows. It does not diagnose, choose treatment, or establish medical reliability; seek appropriate professional care for health decisions.",
                },
                {
                  question: "How often is the medical knowledge base updated?",
                  answer:
                    "The starter corpus is three reviewed CDC source cards with recorded dates and hashes. It is updated only through deliberate review and rebuild steps, so the project makes no currentness guarantee.",
                },
              ].map((faq, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 10 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: index * 0.1 }}
                  viewport={{ once: true }}
                  className="mb-6 border-b border-gray-200 pb-6 last:border-0"
                >
                  <h3 className="text-xl font-semibold text-gray-900 mb-3">{faq.question}</h3>
                  <p className="text-gray-600">{faq.answer}</p>
                </motion.div>
              ))}
            </div>
          </div>
        </section>
      </main>
    </div>
  )
}

export default HomePage
