/**
 * ReasoningSteps — shows the live agentic reasoning process.
 *
 * HOW THIS FITS IN THE FLOW:
 *   1. User switches to Reasoning mode and sends a message
 *   2. Backend yields {"type": "step", "content": "Analyzing question..."}
 *   3. api.js calls onStep("Analyzing question...")
 *   4. ChatView appends the step to the message's reasoningSteps array
 *   5. This component renders those steps in real time
 *   6. When isComplete=true (streaming done), steps collapse by default
 *
 * WHY SHOW REASONING STEPS?
 *   This is the "wow factor" of the project — the user sees the AI thinking:
 *     ✓ Analyzing your question...
 *     ✓ Identified 3 sub-questions to research
 *     ✓ Researching (1/3): What causes diabetic nephropathy?
 *     ✓ Researching (2/3): What are the stages?
 *     ✓ Researching (3/3): How to prevent it?
 *     ✓ Synthesizing all findings into a final answer...
 *   Then the full answer streams in below.
 *
 * Props:
 *   steps      — string[], the reasoning steps that have arrived so far
 *   isComplete — bool, true once the full response has finished streaming
 */

import { useState, useEffect } from "react"
import { Brain, ChevronDown, ChevronUp, CheckCircle, Loader } from "lucide-react"

function ReasoningSteps({ steps, isComplete }) {
  // Start expanded while streaming, collapse automatically when done
  const [expanded, setExpanded] = useState(true)

  useEffect(() => {
    if (isComplete) {
      // Small delay so the user can see the final step before it collapses
      const t = setTimeout(() => setExpanded(false), 1200)
      return () => clearTimeout(t)
    }
  }, [isComplete])

  if (!steps || steps.length === 0) return null

  return (
    <div className="mt-2 mb-3 border border-purple-200 rounded-lg overflow-hidden bg-purple-50">

      {/* Header — always visible, click to toggle */}
      <button
        onClick={() => setExpanded((prev) => !prev)}
        className="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-purple-100 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Brain size={14} className="text-purple-600" />
          <span className="text-xs font-semibold text-purple-700">
            Reasoning process
          </span>
          <span className="text-xs text-purple-500">
            ({steps.length} step{steps.length !== 1 ? "s" : ""})
          </span>
        </div>

        <div className="flex items-center gap-1">
          {/* Spinner while still thinking, checkmark when done */}
          {!isComplete ? (
            <Loader size={12} className="text-purple-500 animate-spin" />
          ) : (
            <CheckCircle size={12} className="text-purple-500" />
          )}
          {expanded ? (
            <ChevronUp size={14} className="text-purple-500" />
          ) : (
            <ChevronDown size={14} className="text-purple-500" />
          )}
        </div>
      </button>

      {/* Step list — only visible when expanded */}
      {expanded && (
        <div className="px-3 pb-3 space-y-1.5">
          {steps.map((step, index) => {
            // The last step is "in progress" if we're still streaming
            const isDone = isComplete || index < steps.length - 1

            return (
              <div key={index} className="flex items-start gap-2">
                {isDone ? (
                  <CheckCircle
                    size={13}
                    className="text-purple-500 mt-0.5 flex-shrink-0"
                  />
                ) : (
                  <Loader
                    size={13}
                    className="text-purple-400 mt-0.5 flex-shrink-0 animate-spin"
                  />
                )}
                <span
                  className={`text-xs leading-relaxed ${
                    isDone ? "text-purple-700" : "text-purple-500"
                  }`}
                >
                  {step}
                </span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default ReasoningSteps
