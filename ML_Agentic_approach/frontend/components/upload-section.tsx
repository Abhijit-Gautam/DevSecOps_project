'use client'

import { useState, useRef } from 'react'
import { Upload, X, File } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'

interface UploadSectionProps {
  onUpload: (file: File, options: UploadOptions) => Promise<void>
  isLoading: boolean
}

export interface UploadOptions {
  run_srlm: boolean
  run_highlights: boolean
  run_fol: boolean
  run_xai: boolean
}

export default function UploadSection({ onUpload, isLoading }: UploadSectionProps) {
  const [file, setFile] = useState<File | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [options, setOptions] = useState<UploadOptions>({
    run_srlm: true,
    run_highlights: true,
    run_fol: true,
    run_xai: true,
  })

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(e.type === 'dragenter' || e.type === 'dragover')
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile) setFile(droppedFile)
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) setFile(e.target.files[0])
  }

  const handleSubmit = async () => {
    if (file) {
      await onUpload(file, options)
      setFile(null)
    }
  }

  return (
    <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-xl p-8 mb-8">
      <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/5 via-purple-500/5 to-transparent pointer-events-none" />
      
      <div className="relative z-10">
        <h2 className="text-2xl font-bold mb-2 bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
          Upload Report
        </h2>
        <p className="text-slate-400 mb-6">Drag and drop your academic report or click to select</p>

        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-2xl p-8 text-center transition-all cursor-pointer ${
            isDragging
              ? 'border-cyan-400 bg-cyan-400/5'
              : 'border-slate-700 hover:border-slate-600'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            onChange={handleFileChange}
            accept=".pdf,.docx,.txt,.md,.log"
            className="hidden"
          />
          
          {file ? (
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <File className="w-8 h-8 text-cyan-400" />
                <div className="text-left">
                  <p className="font-semibold text-white">{file.name}</p>
                  <p className="text-sm text-slate-400">
                    {(file.size / 1024).toFixed(2)} KB
                  </p>
                </div>
              </div>
              <button
                onClick={() => setFile(null)}
                className="p-2 hover:bg-slate-700 rounded-lg transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          ) : (
            <div
              onClick={() => fileInputRef.current?.click()}
              className="cursor-pointer"
            >
              <Upload className="w-12 h-12 text-slate-500 mx-auto mb-3" />
              <p className="text-white font-medium">Click to upload or drag and drop</p>
              <p className="text-sm text-slate-400">PDF, DOCX, TXT, MD, or LOG</p>
            </div>
          )}
        </div>

        <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          {[
            { key: 'run_srlm', label: 'Multi-Agent Eval' },
            { key: 'run_highlights', label: 'Highlighting' },
            { key: 'run_fol', label: 'Logic Verify' },
            { key: 'run_xai', label: 'Explainability' },
          ].map(({ key, label }) => (
            <div key={key} className="flex items-center gap-2">
              <Switch
                checked={options[key as keyof UploadOptions]}
                onCheckedChange={(checked) =>
                  setOptions(prev => ({ ...prev, [key]: checked }))
                }
              />
              <Label className="cursor-pointer text-sm text-slate-300">{label}</Label>
            </div>
          ))}
        </div>

        <Button
          onClick={handleSubmit}
          disabled={!file || isLoading}
          className="w-full h-12 bg-gradient-to-r from-cyan-500 to-purple-500 hover:from-cyan-600 hover:to-purple-600 text-white font-semibold rounded-xl transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Processing...' : 'Evaluate Report'}
        </Button>
      </div>
    </Card>
  )
}
