# 🚀 START HERE - Quick Start Guide

Welcome to the **DevSecOps Report Evaluator Frontend**! This guide will get you up and running in 5 minutes.

## ⚡ Quick Setup (5 minutes)

### 1. Install Dependencies
```bash
pnpm install
```

### 2. Configure Backend URL
```bash
cp .env.example .env.local
```

Edit `.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:5000
```

### 3. Start Development Server
```bash
pnpm dev
```

Visit **http://localhost:3000** in your browser.

### 4. Test Upload
1. Select a report file (PDF, DOCX, TXT)
2. Click "Evaluate Report"
3. Wait for processing (30-60 seconds)
4. Review results

**That's it!** 🎉

---

## 📚 Documentation Guide

Choose your path based on your role:

### 👨‍💻 **For Frontend Developers**
Start with these in order:

1. **[README.md](./README.md)** (5 min read)
   - Feature overview
   - Tech stack
   - Basic setup

2. **[QUICK_REFERENCE.md](./QUICK_REFERENCE.md)** (10 min read)
   - Commands
   - Component map
   - Common fixes
   - Code examples

3. **[ARCHITECTURE.md](./ARCHITECTURE.md)** (15 min read)
   - System design
   - Data flow
   - Component hierarchy
   - API patterns

### 🔧 **For DevOps / Deployment**
Start with these:

1. **[README.md](./README.md)** - Setup overview
2. **[DEPLOYMENT.md](./DEPLOYMENT.md)** - Complete deployment guide
   - 4 deployment options
   - Environment setup
   - Security configuration
   - CI/CD pipeline

### 🐍 **For Backend Developers**
Focus on these:

1. **[API_INTEGRATION.md](./API_INTEGRATION.md)**
   - API endpoints
   - Request/response format
   - Error handling
   - Adding new endpoints

2. **[ARCHITECTURE.md](./ARCHITECTURE.md)**
   - API flow diagrams
   - Data type hierarchy
   - Request/response patterns

### 📊 **For Project Managers**
Read these:

1. **[PROJECT_SUMMARY.md](./PROJECT_SUMMARY.md)**
   - Complete feature list
   - Implementation stats
   - Tech stack overview

2. **[FILE_INVENTORY.md](./FILE_INVENTORY.md)**
   - What was built
   - File statistics
   - Component breakdown

---

## 🎯 Common Tasks

### Need to upload a file?
1. Go to http://localhost:3000
2. Drag & drop a file or click to select
3. Toggle analysis options if needed
4. Click "Evaluate Report"
5. Wait for results

### Want to modify the API URL?
```bash
# .env.local
NEXT_PUBLIC_API_URL=https://your-backend-api.com
```
Then restart: `pnpm dev`

### Need to build for production?
```bash
pnpm build
pnpm start
```

### Want to deploy to Vercel?
See **[DEPLOYMENT.md](./DEPLOYMENT.md)** section "Option 1: Vercel"

### Backend not connecting?
Check **[QUICK_REFERENCE.md](./QUICK_REFERENCE.md)** section "Common Fixes"

---

## 📁 Project Structure at a Glance

```
components/
├── upload-section.tsx         ← File upload form
├── verdict-card.tsx           ← Main results
├── agent-panel.tsx            ← AI agents evaluations
├── highlights-viewer.tsx      ← Text highlighting
├── xai-panel.tsx              ← Explanations
├── fol-verifier.tsx           ← Logic verification
├── thought-timeline.tsx       ← Pipeline steps
└── processing-screen.tsx      ← Loading animation

lib/
├── config.ts                  ← API configuration
├── api-client.ts              ← API functions
└── types.ts                   ← TypeScript definitions

app/
├── page.tsx                   ← Main dashboard
└── layout.tsx                 ← Root layout
```

---

## 🔑 Key Files

| File | Purpose | Read If... |
|------|---------|-----------|
| **README.md** | Feature overview & setup | You're new to the project |
| **QUICK_REFERENCE.md** | Commands & code snippets | You need quick answers |
| **DEPLOYMENT.md** | Deploy to production | You're deploying the app |
| **API_INTEGRATION.md** | API details & debugging | You're fixing API issues |
| **ARCHITECTURE.md** | System design & flows | You want to understand the design |
| **PROJECT_SUMMARY.md** | Complete overview | You need the big picture |

---

## ✅ Checklist: First 10 Minutes

- [ ] Run `pnpm install`
- [ ] Create `.env.local` with API URL
- [ ] Run `pnpm dev`
- [ ] Visit http://localhost:3000
- [ ] Try uploading a test file
- [ ] See results load
- [ ] Click on Agent Panel to expand
- [ ] Check Highlights in the viewer
- [ ] Look at XAI explanations
- [ ] Read PROJECT_SUMMARY.md

---

## 🆘 Need Help?

### Common Issues

**"Cannot connect to backend"**
→ See [QUICK_REFERENCE.md - Common Fixes](./QUICK_REFERENCE.md#-common-fixes)

**"Build fails"**
→ Try: `rm -rf node_modules && pnpm install && pnpm build`

**"Types error"**
→ Make sure `lib/types.ts` exists and is imported

**"API returning 503"**
→ Backend is loading. Wait 30-60 seconds and try again.

### Detailed Troubleshooting
- [README.md Troubleshooting](./README.md#troubleshooting)
- [API_INTEGRATION.md Debugging](./API_INTEGRATION.md#-debugging-api-issues)
- [DEPLOYMENT.md Issues](./DEPLOYMENT.md#troubleshooting-deployment)

---

## 🎨 What You'll See

The application has two main views:

### Upload View (Initial)
- File upload with drag & drop
- Analysis option toggles
- Feature overview cards

### Results View (After Upload)
- Final verdict card (top)
- Multi-agent panel (expandable)
- Text highlights viewer
- XAI explanations panel
- Logic verification panel
- Pipeline timeline

All panels are interactive and fully styled with gradients and smooth animations.

---

## 🚀 Next Steps

### Option 1: Local Development
```bash
pnpm dev
# Make changes, they auto-reload
# Build for production: pnpm build
```

### Option 2: Deploy to Vercel
```bash
# See DEPLOYMENT.md for step-by-step
vercel --prod
```

### Option 3: Deploy to Netlify/Docker
See **[DEPLOYMENT.md](./DEPLOYMENT.md)** for detailed guides

---

## 📞 Support Resources

| Need | Resource |
|------|----------|
| Setup help | [README.md](./README.md) |
| Quick lookup | [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) |
| Deployment | [DEPLOYMENT.md](./DEPLOYMENT.md) |
| API issues | [API_INTEGRATION.md](./API_INTEGRATION.md) |
| System design | [ARCHITECTURE.md](./ARCHITECTURE.md) |
| Full overview | [PROJECT_SUMMARY.md](./PROJECT_SUMMARY.md) |

---

## 🎓 Learn More

### Frontend Architecture
- Components are modular & reusable
- All types are defined in `lib/types.ts`
- API calls use `lib/api-client.ts`
- Styling uses TailwindCSS + shadcn/ui

### Backend Integration
- Type-safe API client included
- Error handling built-in
- All endpoints typed
- Ready for TypeScript projects

### Design System
- Dark mode optimized
- Glassmorphic cards
- Neon gradients
- Smooth animations
- Mobile responsive

---

## 💡 Pro Tips

1. **API URLs**: Use environment variables, not hardcoded strings
2. **Components**: Break down large components into smaller ones
3. **Types**: Always use TypeScript for API responses
4. **Tests**: Add tests as you develop
5. **Deployment**: Use environment variables for different stages

---

## 🎉 You're Ready!

Everything you need is included:
- ✅ 8 production components
- ✅ Type-safe API client
- ✅ Complete documentation
- ✅ Deployment guides
- ✅ Security best practices

**Start with `pnpm dev` and explore!**

---

## 📊 By The Numbers

- **Components**: 8 custom
- **Lines of Code**: 1,316 (components) + 426 (utilities)
- **Documentation**: 2,573 lines
- **TypeScript Types**: 20+ interfaces
- **API Methods**: 13
- **Deployment Options**: 4
- **Troubleshooting Guides**: 20+

---

## 🚀 Let's Go!

```bash
pnpm install
pnpm dev
# Visit http://localhost:3000
# Enjoy! 🎉
```

---

**Questions? Check the docs above. They've got you covered!** 📚

**Happy coding! 💻✨**
