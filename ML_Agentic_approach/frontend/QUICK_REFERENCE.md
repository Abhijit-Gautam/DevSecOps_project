# Quick Reference Guide

Fast lookup for common tasks and commands.

## 🚀 Essential Commands

```bash
# Install dependencies
pnpm install

# Start development server (http://localhost:3000)
pnpm dev

# Build for production
pnpm build

# Start production server
pnpm start

# Run linter
pnpm lint
```

## 📁 File Structure Quick Look

```
Key Files to Know:
├── app/page.tsx                 # Main dashboard logic
├── lib/config.ts                # API endpoint configuration
├── lib/api-client.ts            # API call functions
├── lib/types.ts                 # TypeScript type definitions
├── components/upload-section    # File upload component
├── components/verdict-card      # Main results display
└── .env.example                 # Env vars template (copy to .env.local)
```

## 🔧 Configuration

### Set Backend URL

**Option 1: Environment Variable**
```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:5000
```

**Option 2: Update config.ts**
```typescript
// lib/config.ts
export const API_BASE_URL = 'http://localhost:5000'
```

## 📡 API Usage

### Using API Client
```typescript
import { apiClient } from '@/lib/api-client'

// Upload file
const result = await apiClient.evaluateFile(file, {
  run_srlm: true,
  run_highlights: true,
  run_fol: true,
  run_xai: true,
})

// Get reports
const reports = await apiClient.getReports()

// Health check
const health = await apiClient.healthCheck()
```

### All API Methods
```typescript
apiClient.evaluateFile()           // POST /api/evaluate/upload
apiClient.evaluateText()           // POST /api/evaluate/text
apiClient.getReports()             // GET /api/reports
apiClient.getReport()              // GET /api/reports/{id}
apiClient.deleteReport()           // DELETE /api/reports/{id}
apiClient.getReportHighlights()    // GET /api/reports/{id}/highlights
apiClient.getThoughtProcess()      // GET /api/reports/{id}/thought-process
apiClient.getFOLResult()           // GET /api/reports/{id}/fol
apiClient.getAgentEvaluations()    // GET /api/reports/{id}/agents
apiClient.getXAIExplanation()      // GET /api/reports/{id}/xai
apiClient.getReportText()          // GET /api/reports/{id}/full-text
apiClient.getAnalyticsOverview()   // GET /api/analytics/overview
apiClient.healthCheck()            // GET /api/health
```

## 🎨 Component Map

| Component | File | Purpose | Lines |
|-----------|------|---------|-------|
| Main Dashboard | `app/page.tsx` | Results orchestration | 213 |
| Upload | `upload-section` | File upload & options | 145 |
| Processing | `processing-screen` | Loading animation | 95 |
| Verdict | `verdict-card` | Final assessment | 114 |
| Agents | `agent-panel` | Multi-agent display | 177 |
| Highlights | `highlights-viewer` | Text highlighting | 145 |
| XAI | `xai-panel` | Explainability | 233 |
| FOL | `fol-verifier` | Logic verification | 165 |
| Timeline | `thought-timeline` | Pipeline steps | 129 |

## 🧠 Types Reference

### Main Response Type
```typescript
import type { ReportResponse } from '@/lib/types'

// Has properties:
- report_id: string
- filename: string
- elapsed_ms: number
- status: 'complete' | 'pending' | 'error'
- parsed_data: ParsedData
- roberta_result: RoberTaResult
- unified_verdict: UnifiedVerdict
- agent_evaluations: AgentEvaluation[]
- self_reward_scores: Record<string, number>
- highlight_data: HighlightData
- xai_result: XAIResult
- fol_result: FOLResult
- thought_process: ThoughtStep[]
```

## 🛠️ Debugging

### Check Network Requests
1. DevTools → Network tab
2. Upload file
3. Look for POST request to `/api/evaluate/upload`
4. Check Response tab for data

### Check Console Logs
```typescript
// Add to any component
console.log('[DEBUG]', data)
console.error('[ERROR]', error)
```

### Test Backend
```bash
curl http://localhost:5000/api/health

# Should return:
# {
#   "status": "healthy",
#   "components": {
#     "model": { "status": "ok" },
#     "ollama": { "status": "ok" },
#     "db": { "status": "ok" }
#   }
# }
```

## 🎨 Styling

### Key TailwindCSS Classes
```
Dark backgrounds:  bg-slate-900, bg-slate-800
Text colors:       text-white, text-slate-300, text-slate-400
Gradients:         from-cyan-400 to-purple-400 (text)
Rounded corners:   rounded-2xl, rounded-xl
Spacing:           p-6, gap-4, mb-8
Shadows:           shadow-lg shadow-cyan-500/10
Opacity:           opacity-50, bg-opacity-10
```

### Color Scale for Verdicts
```
Excellent:         from-emerald-500 to-teal-500
Good:              from-cyan-500 to-blue-500
Needs Improvement: from-amber-500 to-orange-500
```

## 📦 Dependencies

### Main Libraries
```json
{
  "next": "16.2.0",
  "react": "^19",
  "typescript": "5.7.3",
  "tailwindcss": "^4.2.0",
  "framer-motion": "^11.0.0",
  "lucide-react": "^0.564.0",
  "react-hook-form": "^7.54.1",
  "zod": "^3.24.1",
  "sonner": "^1.7.1"
}
```

## 🚀 Deployment Commands

### Build
```bash
pnpm build  # Creates .next folder
```

### Environment Setup (Vercel)
1. Go to Project Settings
2. Environment Variables section
3. Add: `NEXT_PUBLIC_API_URL=https://your-backend.com`
4. Redeploy

### Deploy to Vercel
```bash
vercel --prod
```

## 🐛 Common Fixes

| Issue | Fix |
|-------|-----|
| API not connecting | Check `NEXT_PUBLIC_API_URL` in .env.local |
| Build fails | Run `pnpm install` and `pnpm build` |
| Types missing | Ensure `lib/types.ts` is imported |
| Styles not applying | Clear cache: `rm -rf .next && pnpm build` |
| 503 error | Wait for backend models to load (30-60s) |
| CORS error | Check backend CORS configuration |

## 📚 Documentation Links

- [README.md](./README.md) - Full setup & usage (292 lines)
- [DEPLOYMENT.md](./DEPLOYMENT.md) - Deploy guide (428 lines)  
- [API_INTEGRATION.md](./API_INTEGRATION.md) - API details (456 lines)
- [PROJECT_SUMMARY.md](./PROJECT_SUMMARY.md) - Project overview (371 lines)

## 💡 Code Examples

### Adding a New Component
```typescript
// components/my-component.tsx
'use client'

import { Card } from '@/components/ui/card'

export default function MyComponent() {
  return (
    <Card className="bg-slate-800/50 border-slate-600/30">
      {/* Content */}
    </Card>
  )
}
```

### Using Toast Notifications
```typescript
import { useToast } from '@/hooks/use-toast'

export default function MyComponent() {
  const { toast } = useToast()

  const handleClick = () => {
    toast({
      title: 'Success',
      description: 'Operation completed',
    })
  }

  return <button onClick={handleClick}>Click me</button>
}
```

### Error Handling
```typescript
try {
  const data = await apiClient.evaluateFile(file)
  // Handle success
} catch (error) {
  if (error instanceof ApiError) {
    console.error(`API Error ${error.statusCode}:`, error.detail)
  } else {
    console.error('Unknown error:', error)
  }
}
```

## 🔑 Environment Variables

### For Development
```
NEXT_PUBLIC_API_URL=http://localhost:5000
```

### For Production
```
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

### Vercel Project Settings Path
Settings → Environment Variables → Add Variable

## 📊 Component Props

### UploadSection
```typescript
interface Props {
  onUpload: (file: File, options: UploadOptions) => Promise<void>
  isLoading: boolean
}
```

### VerdictCard
```typescript
interface Props {
  verdict: UnifiedVerdict
}
```

### AgentPanel
```typescript
interface Props {
  evaluations: AgentEvaluation[]
  selfRewardScores: Record<string, number>
}
```

## 🎯 Testing API Locally

```bash
# 1. Start backend
cd backend && python app.py

# 2. Start frontend (new terminal)
pnpm dev

# 3. Open http://localhost:3000

# 4. Upload test file
# Check DevTools → Network for requests
# Check DevTools → Console for errors
```

## ✅ Pre-Deployment Checklist

- [ ] Backend is running and healthy
- [ ] `pnpm build` completes without errors
- [ ] Environment variables are set
- [ ] Can upload and evaluate a test file
- [ ] All result panels display correctly
- [ ] Network requests show in DevTools
- [ ] No console errors
- [ ] Mobile layout looks good
- [ ] API URL is correct for production

## 📞 Getting Help

1. Check **Troubleshooting** in README.md
2. Check **Common Issues** in API_INTEGRATION.md
3. Check **Deployment** section in DEPLOYMENT.md
4. Inspect Network tab in DevTools
5. Check terminal logs for backend errors

---

**Quick Reference Complete! 🚀**
