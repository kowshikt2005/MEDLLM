/**
 * SourceCitations — displays which knowledge base documents the LLM used.
 *
 * HOW THIS FITS IN THE FLOW:
 *   1. Backend searches ChromaDB and finds relevant document chunks
 *   2. Those chunks are injected into the LLM's system prompt
 *   3. The LLM answers with those chunks as context
 *   4. The backend sends: { type: "done", sources: [{ source: "diabetes.txt", score: 0.87 }] }
 *   5. api.js passes sources to the onDone callback
 *   6. ChatView stores sources with the assistant message
 *   7. This component renders them as small chips below the message
 *
 * WHY SHOW SOURCES TO THE USER?
 *   Transparency. Without sources, the user has no way to know whether
 *   the LLM is citing a real medical document or hallucinating.
 *   Seeing "Source: diabetes_guide.txt (87% match)" builds trust and lets
 *   users know when to verify the information with their doctor.
 *
 * Props:
 *   sources — array of { source: string, score: number }
 *             e.g. [{ source: "diabetes_guide.txt", score: 0.87 }]
 *             Empty array → render nothing (component returns null)
 */

import { BookOpen } from "lucide-react"

function SourceCitations({ sources }) {
  // Don't render anything if there are no sources.
  // This happens when: knowledge base is empty, or query isn't medically relevant.
  if (!sources || sources.length === 0) return null

  return (
    <div className="mt-2">
      {/* Label */}
      <div className="flex items-center gap-1 text-xs text-gray-400 mb-1">
        <BookOpen size={11} />
        <span>Sources from knowledge base</span>
      </div>

      {/* Source chips */}
      <div className="flex flex-wrap gap-1.5">
        {sources.map((s, index) => {
          // Convert score (0-1) to a percentage for display
          const pct = Math.round(s.score * 100)

          // Color the chip based on relevance score:
          //   ≥ 70% → teal (high confidence)
          //   ≥ 50% → blue (moderate confidence)
          //   < 50% → gray (low confidence, included but worth noting)
          const chipColor =
            pct >= 70
              ? "bg-teal-50 border-teal-200 text-teal-700"
              : pct >= 50
              ? "bg-blue-50 border-blue-200 text-blue-700"
              : "bg-gray-50 border-gray-200 text-gray-600"

          // Strip the file extension for a cleaner display name
          // e.g. "diabetes_guide.txt" → "diabetes_guide"
          const displayName = s.source.replace(/\.[^/.]+$/, "")

          return (
            <span
              key={index}
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-xs font-medium ${chipColor}`}
              title={`${s.source} — ${pct}% relevance`}
            >
              <BookOpen size={10} />
              {displayName}
              <span className="opacity-60">· {pct}%</span>
            </span>
          )
        })}
      </div>
    </div>
  )
}

export default SourceCitations
