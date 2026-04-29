'use client'

import { Card } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Highlighter } from 'lucide-react'

interface HighlightedSpan {
  token: string
  start: number
  end: number
  score: number
}

interface HighlightsViewerProps {
  text: string
  highlightedSpans: HighlightedSpan[]
  threshold: number
}

export default function HighlightsViewer({
  text,
  highlightedSpans,
  threshold,
}: HighlightsViewerProps) {
  const getHighlightColor = (score: number) => {
    if (score > 0.9) return 'bg-red-500/40'
    if (score > 0.8) return 'bg-orange-500/30'
    if (score > 0.7) return 'bg-yellow-500/20'
    return 'bg-cyan-500/20'
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
          Color intensity indicates importance score. Threshold: {(threshold * 100).toFixed(1)}%
        </p>

        <Tabs defaultValue="highlighted" className="w-full">
          <TabsList className="grid w-full grid-cols-2 bg-slate-700/30">
            <TabsTrigger value="highlighted" className="text-slate-300">
              Highlighted View
            </TabsTrigger>
            <TabsTrigger value="legend" className="text-slate-300">
              Legend
            </TabsTrigger>
          </TabsList>

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
                  <p className="font-semibold text-white">Critical (90%+)</p>
                  <p className="text-sm text-slate-400">Highly important signals</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-orange-500/30 rounded" />
                <div>
                  <p className="font-semibold text-white">High (80-90%)</p>
                  <p className="text-sm text-slate-400">Strong importance markers</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-yellow-500/20 rounded" />
                <div>
                  <p className="font-semibold text-white">Medium (70-80%)</p>
                  <p className="text-sm text-slate-400">Moderate importance</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-cyan-500/20 rounded" />
                <div>
                  <p className="font-semibold text-white">Low (below 70%)</p>
                  <p className="text-sm text-slate-400">Background signals</p>
                </div>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </Card>
  )
}
