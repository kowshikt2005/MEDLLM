/**
 * FilePreview — shows attached files as chips below the chat input.
 *
 * Each chip displays:
 *   - An icon based on file type (PDF, image, doc, etc.)
 *   - The filename (truncated if long)
 *   - Upload status: spinner while uploading, checkmark when done, X on error
 *   - A remove button to detach the file
 *
 * Props:
 *   attachments: array of { id, filename, fileType, status }
 *     - status is one of: "uploading", "done", "error"
 *   onRemove: function(index) — called when the user clicks the remove button
 */

import { FileText, Image, File, X, Check, AlertCircle } from "lucide-react"

function FilePreview({ attachments, onRemove }) {
  if (!attachments || attachments.length === 0) return null

  // Pick an icon based on the file type
  const getIcon = (fileType) => {
    switch (fileType) {
      case "pdf":
      case "docx":
      case "text":
        return <FileText size={16} />
      case "image":
        return <Image size={16} />
      default:
        return <File size={16} />
    }
  }

  // Pick a status indicator
  const getStatusIcon = (status) => {
    switch (status) {
      case "uploading":
        return (
          <div className="w-3.5 h-3.5 border-2 border-teal-500 border-t-transparent rounded-full animate-spin" />
        )
      case "done":
        return <Check size={14} className="text-green-600" />
      case "error":
        return <AlertCircle size={14} className="text-red-500" />
      default:
        return null
    }
  }

  // Truncate long filenames
  const truncate = (name, maxLen = 24) => {
    if (name.length <= maxLen) return name
    const ext = name.slice(name.lastIndexOf("."))
    return name.slice(0, maxLen - ext.length - 3) + "..." + ext
  }

  return (
    <div className="flex flex-wrap gap-2 px-2 pb-2">
      {attachments.map((att, index) => (
        <div
          key={att.id || index}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm border transition-colors ${
            att.status === "error"
              ? "bg-red-50 border-red-200 text-red-700"
              : att.status === "uploading"
                ? "bg-teal-50 border-teal-200 text-teal-700"
                : "bg-gray-100 border-gray-200 text-gray-700"
          }`}
        >
          {getIcon(att.fileType)}
          <span className="max-w-[160px] truncate">{truncate(att.filename)}</span>
          {getStatusIcon(att.status)}
          <button
            onClick={() => onRemove(index)}
            className="ml-1 p-0.5 rounded-full hover:bg-gray-200 transition-colors"
            aria-label={`Remove ${att.filename}`}
          >
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  )
}

export default FilePreview
