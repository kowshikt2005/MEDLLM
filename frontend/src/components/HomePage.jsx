"use client"

import { useEffect, useState } from "react"
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
  const [activeTestimonial, setActiveTestimonial] = useState(0)

  // Parallax effect for background elements
  const bgParallax1 = useTransform(scrollY, [0, 1000], [0, -150])
  const bgParallax2 = useTransform(scrollY, [0, 1000], [0, -100])

  useEffect(() => {
    // Testimonial rotation
    const interval = setInterval(() => {
      setActiveTestimonial((prev) => (prev + 1) % testimonials.length)
    }, 5000)

    return () => clearInterval(interval)
  }, [])

  const features = [
    {
      icon: Brain,
      title: "Advanced AI Diagnostics",
      description:
        "Our cutting-edge LLM technology analyzes medical data with unprecedented accuracy, providing insights that might be missed in traditional diagnostics.",
    },
    {
      icon: Shield,
      title: "Multimodal inputs",
      description:
        "This model could take text,image and any document as input for anylysis",
    },
    {
      icon: Activity,
      title: "Real-time Monitoring",
      description:
        "Continuous health tracking with personalized recommendations based on your unique medical profile and latest health research.",
    },
    {
      icon: FileText,
      title: "Comprehensive Reports",
      description:
        "Detailed medical reports with visualized data and plain-language explanations of complex medical concepts.",
    },
    {
      icon: Microscope,
      title: "Research-Backed Insights",
      description:
        "Our RAG system continuously integrates the latest medical research to provide evidence-based recommendations.",
    },
    {
      icon: Stethoscope,
      title: "Physician Collaboration",
      description:
        "Seamlessly share insights with your healthcare providers to enhance your medical care coordination.",
    },
  ]

  const workflowSteps = [
    {
      icon: FileText,
      title: "Upload Medical Data",
      description: "Securely upload your medical records, test results, and imaging scans.",
    },
    {
      icon: Brain,
      title: "AI Analysis",
      description: "Our advanced LLM processes your data using RAG technology to extract meaningful insights.",
    },
    {
      icon: HeartPulse,
      title: "Personalized Diagnostics",
      description: "Receive detailed diagnostic insights tailored to your specific health profile.",
    },
    {
      icon: Pill,
      title: "Treatment Recommendations",
      description: "Get evidence-based treatment options and preventive care suggestions.",
    },
    {
      icon: Clock,
      title: "Follow-up Monitoring",
      description: "Continuous monitoring and adjustments based on your progress and new data.",
    },
  ]

  const testimonials = [
    {
      quote:
        "MedLLM helped identify a rare condition that my doctors had missed for years. The personalized insights were life-changing.",
      author: "Sarah J., Patient",
      rating: 5,
    },
    {
      quote:
        "As a physician, I've found MedLLM to be an invaluable second opinion. It helps me catch details I might otherwise overlook.",
      author: "Dr. Michael Chen, Cardiologist",
      rating: 5,
    },
    {
      quote:
        "The integration of latest research with my personal health data provided insights that significantly improved my treatment plan.",
      author: "Robert T., Patient",
      rating: 5,
    },
  ]

  const stats = [
    { value: "80.0%", label: "Diagnostic Accuracy" },
    { value: "Uptodate", label: "Medical Papers Analyzed" },
    { value: "Robust", label: "Compared to Traditional Methods" },
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
              The Future of
              <span className="text-[#4f8684] block mt-2">Medical Diagnostics</span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.2 }}
              className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto"
            >
              Experience healthcare powered by advanced AI, providing personalized medical insights and recommendations
              based on your unique health profile and the latest medical research.
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
                <CheckCircle2 className="h-4 w-4 mr-2 text-teal-600" /> Clinically Validated
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
                Powerful Features
              </div>
              <h2 className="text-4xl font-bold text-gray-900 mb-4">Why Choose MedLLM?</h2>
              <p className="text-xl text-gray-600 max-w-3xl mx-auto">
                Revolutionizing healthcare with AI-powered insights that combine the latest medical research with your
                personal health data
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
                Our streamlined process combines your medical data with advanced AI to deliver personalized insights
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
                  MedLLM combines the power of large language models with a vast knowledge base of medical literature,
                  clinical guidelines, and real-time data to provide accurate, personalized medical insights.
                </p>
                <ul className="space-y-4">
                  {[
                    "Processes complex medical data including patient records, lab results, and imaging scans",
                    "Provides evidence-based recommendations with citations to medical literature",
                    "Explains complex medical concepts in easy-to-understand language",
                    "Identifies patterns and correlations that might be missed in traditional analysis",
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
                          <span className="text-purple-600">Patient:</span> I've been experiencing frequent headaches
                          and fatigue for the past month.
                        </p>
                      </div>
                      <div className="bg-teal-50 rounded-lg p-3">
                        <p className="text-gray-800 font-mono text-sm">
                          <span className="text-teal-600">MedLLM:</span> Based on your symptoms and medical history,
                          I've identified several potential causes. Your recent blood work shows slightly low iron
                          levels which could contribute to fatigue.
                        </p>
                      </div>
                      <div className="bg-teal-50 rounded-lg p-3">
                        <p className="text-gray-800 font-mono text-sm">
                          <span className="text-teal-600">MedLLM:</span> According to recent research in the Journal of
                          Neurology (2023), your symptom pattern is consistent with tension headaches, possibly
                          exacerbated by the screen time increase noted in your activity logs.
                        </p>
                      </div>
                      <div className="bg-teal-50 rounded-lg p-3">
                        <p className="text-gray-800 font-mono text-sm">
                          <span className="text-teal-600">MedLLM:</span> Recommended actions: 1) Iron-rich diet or
                          supplements, 2) Regular screen breaks using the 20-20-20 rule, 3) Stress management
                          techniques. Would you like detailed information on any of these recommendations?
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
              <h2 className="text-4xl font-bold mb-6">Ready to Transform Your Healthcare Experience?</h2>
              <p className="text-xl mb-8">
                Complete your health profile for personalized medical insights and recommendations backed by the latest
                research and AI technology.
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
                Everything you need to know about MedLLM and how it can help you
              </p>
            </motion.div>

            <div className="max-w-3xl mx-auto">
              {[
                {
                  question: "How accurate is MedLLM's diagnostic assistance?",
                  answer:
                    "MedLLM achieves 99.8% accuracy in diagnostic assistance when compared to expert consensus. Our system is continuously trained on the latest medical research and validated by leading healthcare professionals. However, MedLLM is designed to assist healthcare providers, not replace them.",
                },
                {
                  question: "How does Retrieval-Augmented Generation work?",
                  answer:
                    "Retrieval-Augmented Generation (RAG) combines large language models with a knowledge base of medical literature. When you input your health data, MedLLM retrieves relevant medical information from peer-reviewed journals, clinical guidelines, and medical databases, then generates personalized insights based on this information and your specific health profile.",
                },
                {
                  question: "Can MedLLM replace my doctor?",
                  answer:
                    "No, MedLLM is designed to complement, not replace, healthcare professionals. It provides additional insights, helps identify patterns, and suggests potential considerations based on the latest research, but final diagnostic and treatment decisions should always be made by qualified healthcare providers.",
                },
                {
                  question: "How often is the medical knowledge base updated?",
                  answer:
                    "Our medical knowledge base is updated daily with the latest peer-reviewed research, clinical guidelines, and medical advancements. This ensures that the insights provided are based on the most current medical knowledge available.",
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
