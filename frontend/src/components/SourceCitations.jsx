/**
 * Retrieved-source chips shown below a supported normal-mode answer.
 *
 * A percentage here is retrieval relevance only. It says how closely a chunk
 * matched the query in this index; it is not a medical-confidence score.
 */

import { BookOpen } from "lucide-react"

function SourceCitations({ sources }) {
  if (!sources || sources.length === 0) return null

  return (
    <div className="mt-2">
      <div className="flex items-center gap-1 text-xs text-gray-500 mb-1">
        <BookOpen size={11} />
        <span>Retrieved references</span>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {sources.map((source, index) => {
          const rawScore = Number(source.score ?? 0)
          const relevance = Math.round(Math.max(0, Math.min(1, rawScore)) * 100)
          const sourceLabel = String(source.source || "Unknown source")
          const sourceKind = source.corpus === "curated" ? "Curated source" : "Retrieved document"
          const chip = (
            <>
              <BookOpen size={10} />
              <span>{sourceLabel}</span>
              <span className="opacity-70">· {sourceKind} · {relevance}% relevance</span>
            </>
          )
          const className = "inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-xs font-medium bg-teal-50 border-teal-200 text-teal-800 hover:bg-teal-100"
          const title = `${sourceLabel} — ${relevance}% retrieval relevance`

          return source.url ? (
            <a
              key={source.source_id || source.url || index}
              href={source.url}
              target="_blank"
              rel="noreferrer"
              className={className}
              title={`Open original source: ${title}`}
            >
              {chip}
            </a>
          ) : (
            <span key={source.source_id || index} className={className} title={title}>
              {chip}
            </span>
          )
        })}
      </div>
    </div>
  )
}

export default SourceCitations
