# DevSecOps Report Evaluator - Frontend

A premium, production-ready Next.js frontend for the AI-powered academic report evaluator. Built with TypeScript, TailwindCSS, shadcn/ui, and Framer Motion.

## 🎨 Design Philosophy

- **Futuristic AI Research Dashboard** inspired by Linear.app, Vercel, and Perplexity
- **Glassmorphism & Neon Gradients** for premium aesthetic
- **Dark mode first** with elegant contrast
- **Smooth micro-interactions** for delightful UX
- **Fully responsive** mobile-first design

## 🚀 Features

### Core Functionality
- **File Upload** - Drag & drop support for PDF, DOCX, TXT, MD, LOG files
- **Processing Visualization** - Animated AI pipeline progress indicator
- **Results Dashboard** - Comprehensive multi-section evaluation display

### Analysis Panels
1. **Final Verdict Card** - Overall assessment, confidence, and recommendations
2. **Multi-Agent Panel** - Individual evaluations from 6 specialized AI agents
3. **Text Highlighting** - Visual importance scoring of report tokens
4. **XAI Analysis** - Explainable AI with decision factors and improvement roadmap
5. **FOL Verification** - Formal logic consistency checking with axiom details
6. **Thought Timeline** - Visual pipeline steps with evidence trails

### Advanced Features
- Real-time API integration with Flask backend
- Accordion-based expandable sections for detailed information
- Badge-based status indicators (color-coded by verdict)
- Evidence extraction and display
- Improvement roadmap with priority ranking
- Counterfactual scenarios (what-if analysis)
- FOL axiom verification details

## 🛠️ Tech Stack

- **Framework**: Next.js 16 (App Router)
- **Language**: TypeScript
- **UI Library**: shadcn/ui
- **Styling**: TailwindCSS v4
- **Animations**: Framer Motion
- **Icons**: Lucide React
- **Form Handling**: React Hook Form + Zod
- **Notifications**: Sonner Toast

## 📦 Setup & Installation

### Prerequisites
- Node.js 18+ (or use pnpm)
- Backend API running on `http://localhost:5000`

### Installation

1. **Clone or download the project**
```bash
cd my-project
```

2. **Install dependencies**
```bash
pnpm install
# or npm install, yarn install, bun install
```

3. **Configure environment variables**
```bash
cp .env.example .env.local
# Edit .env.local to set your API URL
```

4. **Start development server**
```bash
pnpm dev
```

Visit `http://localhost:3000` in your browser.

## 🔧 Configuration

### Environment Variables

Create a `.env.local` file:

```env
# Backend API URL (default: http://localhost:5000)
NEXT_PUBLIC_API_URL=http://localhost:5000
```

If deploying to Vercel:
1. Go to project settings → Environment Variables
2. Add `NEXT_PUBLIC_API_URL` pointing to your backend domain
3. Example: `https://api.yourcompany.com`

## 📁 Project Structure

```
components/
├── upload-section.tsx       # File upload with drag-drop
├── processing-screen.tsx    # AI pipeline visualization
├── verdict-card.tsx         # Final verdict display
├── agent-panel.tsx          # Multi-agent evaluations
├── highlights-viewer.tsx    # Text importance highlighting
├── xai-panel.tsx           # Explainability analysis
├── fol-verifier.tsx        # Logic verification
├── thought-timeline.tsx    # Pipeline steps timeline
└── ui/                      # shadcn/ui components

app/
├── page.tsx                # Main dashboard page
├── layout.tsx              # Root layout with gradients
└── globals.css             # Global styles

lib/
├── config.ts               # API configuration
└── utils.ts                # Utility functions

public/                      # Static assets
```

## 🎨 Customization

### Colors & Theme

Edit `app/globals.css` to customize the color scheme. The design uses:
- **Primary gradient**: Cyan → Blue → Purple
- **Dark backgrounds**: Slate 900-950
- **Accent colors**: Emerald (success), Amber (warning), Red (error)

### API Integration

All API calls are configured in `lib/config.ts`. Update `NEXT_PUBLIC_API_URL` to point to your backend.

### Component Styling

All components use TailwindCSS with consistent spacing, shadows, and animations. Modify `tailwind.config.ts` for design token adjustments.

## 🚀 Deployment

### Deploy to Vercel (Recommended)

1. **Push to GitHub**
```bash
git add .
git commit -m "Initial commit"
git push origin main
```

2. **Import to Vercel**
   - Visit https://vercel.com/new
   - Select your GitHub repository
   - Configure environment variables (add `NEXT_PUBLIC_API_URL`)
   - Click Deploy

3. **Set Backend URL**
   - After deployment, update environment variable with your backend API domain
   - Example: `https://api.yourdomain.com`

### Deploy to Other Platforms

**Netlify, Render, Railway, etc.**
```bash
# Build production bundle
pnpm build

# Start production server
pnpm start
```

Ensure environment variables are set in your platform's dashboard.

## 🔌 Backend Integration

### API Endpoints Used

The frontend connects to these Flask backend endpoints:

- `POST /api/evaluate/upload` - Upload and evaluate report file
- `POST /api/evaluate/text` - Evaluate report as raw text
- `GET /api/reports` - List all reports
- `GET /api/health` - Health check

### Response Handling

The frontend expects the standard response format from your backend (see `BACKEND.md` for schema). Key components:
- `unified_verdict` - Main evaluation result
- `agent_evaluations` - Individual agent assessments
- `highlight_data` - Token importance scores
- `xai_result` - Explainability analysis
- `fol_result` - Logic verification details
- `thought_process` - Pipeline execution steps

### Error Handling

- **Network errors** → Toast notification with retry option
- **API errors** → Descriptive error messages
- **Loading states** → Processing screen animation
- **Missing data** → Graceful fallbacks

## 🎯 Usage Guide

### Uploading a Report

1. Drag and drop or click to select a file
2. (Optional) Toggle analysis features:
   - Multi-Agent Evaluation (SRLM)
   - Text Highlighting
   - Logic Verification (FOL)
   - Explainability (XAI)
3. Click "Evaluate Report"
4. Wait for processing (typically 30-60 seconds)
5. Review results across all panels

### Understanding Results

**Final Verdict Card**
- Shows overall assessment and confidence
- Lists key strengths, weaknesses, and recommendations

**Multi-Agent Panel**
- Expandable cards for each AI agent
- Shows individual scores and reasoning
- Self-reward quality scores

**Highlighted Report Viewer**
- Color-coded importance: Red (critical) → Cyan (low)
- Hover to see exact importance score
- Side panel legend for reference

**XAI Analysis**
- **Explanation tab**: Model reasoning and attention summary
- **Key Signals tab**: Decision factors with impact direction
- **Roadmap tab**: Priority-ranked improvements
- **What-If tab**: Counterfactual scenarios

**FOL Verification**
- Consistency score and status
- Green badges = satisfied axioms
- Red badges = violated rules
- Click to expand for detailed reasoning

**Thought Timeline**
- Visual pipeline execution flow
- Each step with icon, title, and evidence
- Color-coded by analysis type

## 🐛 Troubleshooting

### "Failed to connect to API"
- Verify backend is running on `http://localhost:5000`
- Check `NEXT_PUBLIC_API_URL` environment variable
- Ensure CORS is enabled on backend (usually in Flask config)

### Processing takes too long
- Large files (>1 MB) may take 2-3 minutes
- Backend may be loading models on first run
- Check backend logs for errors

### Results not displaying correctly
- Verify backend response matches schema in `BACKEND.md`
- Check browser console for JavaScript errors
- Try refreshing the page

### Styling looks broken
- Clear browser cache (Ctrl+Shift+Delete)
- Restart dev server (`pnpm dev`)
- Verify TailwindCSS is building properly

## 📚 Additional Resources

- [Backend Documentation](./user_read_only_context/text_attachments/BACKEND-0auf9.md)
- [Next.js Documentation](https://nextjs.org/docs)
- [shadcn/ui Components](https://ui.shadcn.com)
- [TailwindCSS Docs](https://tailwindcss.com)

## 📝 License

This project is provided as-is for educational and research purposes.

## 🤝 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review backend logs for API errors
3. Inspect browser DevTools console for frontend errors
4. Verify environment variables are correctly set

---

**Built with ❤️ for premium AI-powered report evaluation**
