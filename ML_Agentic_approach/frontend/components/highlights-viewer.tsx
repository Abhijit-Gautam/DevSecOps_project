'use client'

import { useMemo, useState } from 'react'
import { Card } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { FileText, Highlighter } from 'lucide-react'
import type { PdfAnnotation } from '@/lib/types'

interface HighlightedSpan {
  token: string
  start: number
  end: number
  score: number
}

interface HighlightsViewerProps {
  text: string
  highlightedSpans: HighlightedSpan[]
  pdfAnnotations?: PdfAnnotation[]
  pdfUrl?: string | null
  threshold: number
}

export default function HighlightsViewer({
  text,
  highlightedSpans,
  pdfAnnotations = [],
  pdfUrl,
  threshold,
}: HighlightsViewerProps) {
  const [activeAnnotation, setActiveAnnotation] = useState<PdfAnnotation | null>(null)
  const pageCount = useMemo(
    () => Math.max(1, ...pdfAnnotations.map((item) => item.page_number || 1)),
    [pdfAnnotations]
  )

  const getHighlightColor = (score: number) => {
    if (score > 0.9) return 'bg-red-500/40'
    if (score > 0.8) return 'bg-orange-500/30'
    if (score > 0.7) return 'bg-yellow-500/20'
    return 'bg-cyan-500/20'
  }

  const markerClass = (color: string) => {
    if (color === 'green') return 'bg-green-400/35 border-green-300 hover:bg-green-400/50'
    if (color === 'red') return 'bg-red-500/35 border-red-300 hover:bg-red-500/50'
    return 'bg-yellow-300/45 border-yellow-200 hover:bg-yellow-300/60'
  }

  const renderPdfViewer = () => {
    if (!pdfUrl) return null

    return (
      <div className="space-y-4">
        <div className="relative h-[720px] overflow-hidden rounded-lg border border-slate-600/30 bg-slate-950">
          <iframe
            src={pdfUrl}
            title="Original PDF report"
            className="absolute inset-0 h-full w-full bg-white"
          />
          <div className="pointer-events-none absolute inset-0">
            {pdfAnnotations.map((annotation, idx) => {
              const rect = annotation.rect ?? { x: 7, y: 8, width: 86, height: 5 }
              const top = (((annotation.page_number || 1) - 1 + rect.y / 100) / pageCount) * 100
              const height = Math.max(2.4, rect.height / pageCount)
              return (
                <button
                  key={`${annotation.agent}-${idx}-${annotation.text_span}`}
                  type="button"
                  className={`pointer-events-auto absolute rounded-sm border text-left shadow-lg transition ${markerClass(annotation.color)}`}
                  style={{
                    left: `${rect.x}%`,
                    top: `${Math.min(96, top)}%`,
                    width: `${rect.width}%`,
                    height: `${height}%`,
                  }}
                  title={`${annotation.issue_type} (${annotation.severity}): ${annotation.explanation}`}
                  onMouseEnter={() => setActiveAnnotation(annotation)}
                  onFocus={() => setActiveAnnotation(annotation)}
                  onClick={() => setActiveAnnotation(annotation)}
                >
                  <span className="sr-only">{annotation.explanation}</span>
                </button>
              )
            })}
          </div>
        </div>

        {activeAnnotation && (
          <div className="rounded-lg border border-slate-600/40 bg-slate-900/95 p-4 shadow-xl">
            <div className="mb-2 flex flex-wrap items-center gap-2 text-xs">
              <span className="rounded bg-slate-700 px-2 py-1 text-slate-200">
                Page {activeAnnotation.page_number}
              </span>
              <span className="rounded bg-slate-700 px-2 py-1 text-slate-200">
                {activeAnnotation.issue_type}
              </span>
              <span className="rounded bg-slate-700 px-2 py-1 text-slate-200">
                {activeAnnotation.severity}
              </span>
              <span className="rounded bg-slate-700 px-2 py-1 text-slate-200">
                Impact {activeAnnotation.score_impact > 0 ? '+' : ''}{activeAnnotation.score_impact}
              </span>
            </div>
            <p className="mb-2 text-sm font-medium text-white">{activeAnnotation.text_span}</p>
            <p className="text-sm text-slate-300">{activeAnnotation.explanation}</p>
            {activeAnnotation.suggestion && (
              <p className="mt-2 text-sm text-cyan-200">{activeAnnotation.suggestion}</p>
            )}
            {activeAnnotation.agent && (
              <p className="mt-2 text-xs text-slate-500">Marked by {activeAnnotation.agent}</p>
            )}
          </div>
        )}
      </div>
    )
  }

  // Build highlighted text
  const renderHighlightedText = () => {
    if (!highlightedSpans || highlightedSpans.length === 0) {
      return <p className="text-slate-300 leading-relaxed">{text}</p>
    }

    const parts: React.ReactNode[] = []
    let lastEnd = 0

    const sortedSpans = [...highlightedSpans].sort((a, b) => a.start - b.start)

    sortedSpans.forEach((span, idx) => {
      // Add text before highlight
      if (span.start > lastEnd) {
        parts.push(
          <span key={`text-${idx}`} className="text-slate-300">
            {text.slice(lastEnd, span.start)}
          </span>
        )
      }

      // Add highlighted text
      parts.push(
        <span
          key={`highlight-${idx}`}
          className={`${getHighlightColor(span.score)} px-1 rounded transition hover:opacity-80 cursor-help`}
          title={`Score: ${(span.score * 100).toFixed(1)}%`}
        >
          {text.slice(span.start, span.end)}
        </span>
      )

      lastEnd = span.end
    })

    // Add remaining text
    if (lastEnd < text.length) {
      parts.push(
        <span key="text-end" className="text-slate-300">
          {text.slice(lastEnd)}
        </span>
      )
    }

    return <p className="text-slate-300 leading-relaxed">{parts}</p>
  }

  return (
    <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-xl p-8 mb-8">
      <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/5 via-purple-500/5 to-transparent pointer-events-none" />

      <div className="relative z-10">
        <h3 className="text-2xl font-bold mb-2 text-white flex items-center gap-2">
          <Highlighter className="w-6 h-6 text-cyan-400" />
          Highlighted Report Viewer
        </h3>
        <p className="text-slate-400 mb-6">
          {pdfUrl
            ? 'Original PDF with agent issue and strength highlights.'
            : `Color intensity indicates importance score. Threshold: ${(threshold * 100).toFixed(1)}%`}
        </p>

        <Tabs defaultValue={pdfUrl ? 'pdf' : 'highlighted'} className="w-full">
          <TabsList className="grid w-full grid-cols-3 bg-slate-700/30">
            {pdfUrl && (
              <TabsTrigger value="pdf" className="text-slate-300">
                <FileText className="mr-2 h-4 w-4" />
                PDF View
              </TabsTrigger>
            )}
            <TabsTrigger value="highlighted" className="text-slate-300">
              Text View
            </TabsTrigger>
            <TabsTrigger value="legend" className="text-slate-300">
              Legend
            </TabsTrigger>
          </TabsList>

          {pdfUrl && (
            <TabsContent value="pdf" className="mt-6">
              {renderPdfViewer()}
            </TabsContent>
          )}

          <TabsContent value="highlighted" className="mt-6">
            <div className="bg-slate-800/50 border border-slate-600/30 rounded-lg p-6 max-h-96 overflow-y-auto">
              {renderHighlightedText()}
            </div>
          </TabsContent>

          <TabsContent value="legend" className="mt-6">
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-red-500/40 rounded" />
                <div>
                  <p className="font-semibold text-white">Red</p>
                  <p className="text-sm text-slate-400">Bad or weak sentence, high severity issue</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-green-500/35 rounded" />
                <div>
                  <p className="font-semibold text-white">Green</p>
                  <p className="text-sm text-slate-400">Good or strong evidence</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-yellow-300/45 rounded" />
                <div>
                  <p className="font-semibold text-white">Yellow</p>
                  <p className="text-sm text-slate-400">Warning, formatting issue, or diagram issue</p>
                </div>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </Card>
  )
}
