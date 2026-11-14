# Skille Claude dla tego repozytorium

Claude Code wczytuje ten katalog automatycznie na starcie każdej sesji z tym repozytorium
(w chmurze i lokalnie). Każdy podkatalog to jeden skill (`SKILL.md` + materiały).
Źródła i licencje: `THIRD_PARTY.md`. Skille działają z uprawnieniami Claude, więc nowe
dodawaj dopiero po przeczytaniu ich treści i skryptów.

**Uwaga:** część skilli finansowych (`*-reader`, `tradingview-*`) wymaga zainstalowania na
komputerze dodatkowych narzędzi (`opencli`, `tdl`, `uv`) i korzysta z zalogowanej sesji
w przeglądarce Chrome. W sesji w chmurze nie zadziałają.

Inne skille z dodatkowymi wymaganiami:
- `graphify` przy pierwszym użyciu instaluje pakiet `graphifyy` z PyPI.
- `obsidian-cli` wymaga aplikacji Obsidian, a `obsidian-headless`, `defuddle` i `knap` swoich narzędzi CLI.
- `last30days` działa bez kluczy, ale część źródeł (X, YouTube, TikTok) wymaga kluczy API lub narzędzi (`/last30days doctor`).
- `design` i `banner-design` do generowania obrazów potrzebują klucza API (Gemini i inne).

| Skill | Opis (z SKILL.md) | Źródło |
|---|---|---|
| `ab-testing` | When the user wants to plan, run, or read A/B tests, or asks a judgement call on one: is the result real, can … | coreyhaines31/marketingskills |
| `ad-creative` | When the user wants to write or judge ad creative, or asks which ad, hook, or angle to run or kill: headlines,… | coreyhaines31/marketingskills |
| `ads` | When the user wants to plan, run, or fix paid ads on Google, Meta, and LinkedIn, or asks a judgement call on t… | coreyhaines31/marketingskills |
| `ai-seo` | When the user wants to get cited and recommended in AI answers (ChatGPT, Perplexity, AI Overviews), or asks wh… | coreyhaines31/marketingskills |
| `analytics` | When the user wants to set up or audit analytics, or asks whether a metric or number is calculated right, what… | coreyhaines31/marketingskills |
| `android-build` | Use when building, testing, signing, releasing or delivering the Android app in gps-app/ (Moja pozycja GPS), w… | własny (to repozytorium) |
| `archify` | Create validated architecture, workflow, sequence, data-flow, lifecycle/state, ERD, class, tree, timeline, and… | tt-a1i/archify |
| `aso` | When the user wants to audit or optimize an App Store or Google Play listing, or asks which title, keywords, o… | coreyhaines31/marketingskills |
| `attribution` | When the user wants to work out which marketing drives revenue, or asks whether a channel is really working, w… | coreyhaines31/marketingskills |
| `banner-design` | Design banners for social media, ads, website heroes, creative assets, and print. Multiple art direction optio… | nextlevelbuilder/ui-ux-pro-max-skill |
| `brainstorming` | You MUST use this before any creative work - creating features, building components, adding functionality, mod… | obra/superpowers |
| `brand` | Brand voice, visual identity, messaging frameworks, asset management, brand consistency. Activate for branded … | nextlevelbuilder/ui-ux-pro-max-skill |
| `canvas-design` | Create beautiful visual art in .png and .pdf documents using design philosophy. You should use this skill when… | anthropics/skills |
| `caveman` | Terse caveman voice: answer first, fluff gone, every technical fact kept. Use for /caveman, "caveman mode", "t… | JuliusBrussee/caveman |
| `caveman-commit` | Write a Conventional Commits message compressed to intent only. Use for "write a commit", "commit message", /c… | JuliusBrussee/caveman |
| `caveman-compress` | Compress a memory file such as CLAUDE.md or a todo list into caveman format to save input tokens, keeping a re… | JuliusBrussee/caveman |
| `caveman-help` | Quick-reference card for the three caveman skills and their commands. Trigger: /caveman-help or "caveman help"… | JuliusBrussee/caveman |
| `caveman-review` | Compressed code review - one line per finding with location, problem and fix. Use for /caveman-review, "review… | JuliusBrussee/caveman |
| `churn-prevention` | When the user wants to reduce churn, or asks why customers cancel, whether to offer a discount or pause: cance… | coreyhaines31/marketingskills |
| `co-marketing` | When the user wants co-marketing partners or joint campaigns, or asks whether a partner fits, a size mismatch … | coreyhaines31/marketingskills |
| `cold-email` | When the user wants to write or run B2B cold outbound, or asks whether an opener, reason to reach out, or emai… | coreyhaines31/marketingskills |
| `community-marketing` | When the user wants to build or grow an online community, or asks whether a community is worth it, where to ho… | coreyhaines31/marketingskills |
| `company-valuation` | > | himself65/finance-skills |
| `competitor-profiling` | When the user wants to research competitors into dated profiles, or asks what a rival charges, claims, or is d… | coreyhaines31/marketingskills |
| `competitors` | When the user wants to create or audit comparison and alternative pages ('X vs Y', 'X alternative', 'best X al… | coreyhaines31/marketingskills |
| `content-strategy` | When the user wants to plan content, or asks which topic or piece to prioritize, what to write about, or why p… | coreyhaines31/marketingskills |
| `conversion-tracking` | When the user wants to set up, audit, or fix conversion tracking to Google Ads, Meta, GA4, LinkedIn, and TikTo… | coreyhaines31/marketingskills |
| `copy-editing` | When the user wants to edit, tighten, proofread, or refresh existing copy, or asks whether to keep, cut, or ch… | coreyhaines31/marketingskills |
| `copywriting` | When the user wants to write or rewrite page copy (homepage, landing, pricing, feature), or asks which headlin… | coreyhaines31/marketingskills |
| `cro` | When the user wants more conversions from a page or form, or asks why a page isn't converting, what to change … | coreyhaines31/marketingskills |
| `customer-research` | When the user wants to run or synthesize customer research, or asks what customer quotes, reviews, or feedback… | coreyhaines31/marketingskills |
| `defuddle` | Extract clean Markdown from HTML pages with Defuddle CLI. | obsidianmd/obsidian-skills |
| `design` | Comprehensive design skill: brand identity, design tokens, UI styling, logo generation (55 styles, Gemini, Atl… | nextlevelbuilder/ui-ux-pro-max-skill |
| `design-system` | Token architecture, component specifications, and slide generation. Three-layer tokens (primitive→semantic→com… | nextlevelbuilder/ui-ux-pro-max-skill |
| `diagnosing-superpowers` | Use when a superpowers session went wrong and your human partner wants to know why — repeated work, ignored pl… | obra/superpowers |
| `directory-submissions` | When the user wants to list a product in startup, SaaS, AI, MCP, and review directories, or asks which directo… | coreyhaines31/marketingskills |
| `discord-reader` | > | himself65/finance-skills |
| `dispatching-parallel-agents` | Use when facing 2+ independent tasks that can be worked on without shared state or sequential dependencies | obra/superpowers |
| `doc-coauthoring` | Guide users through a structured workflow for co-authoring documentation. Use when user wants to write documen… | anthropics/skills |
| `docx` | Use this skill whenever the user wants to create, read, edit, or manipulate Word documents (.docx files) or Wo… | anthropics/skills |
| `earnings-preview` | > | himself65/finance-skills |
| `earnings-recap` | > | himself65/finance-skills |
| `emails` | When the user wants to create or improve automated email sequences, or asks what to send, when, or whether an … | coreyhaines31/marketingskills |
| `estimate-analysis` | > | himself65/finance-skills |
| `etf-premium` | > | himself65/finance-skills |
| `events` | When the user wants to plan, run, sponsor, or speak at events, or asks whether an event or booth is worth the … | coreyhaines31/marketingskills |
| `executing-plans` | Use when executing an implementation plan in the current session as the implementer yourself — your human part… | obra/superpowers |
| `finance-sentiment` | > | himself65/finance-skills |
| `find-skills` | Helps users discover and install agent skills when they ask questions like "how do I do X", "find a skill for … | vercel-labs/skills |
| `finishing-a-development-branch` | Use when implementation is complete, all tests pass, and you need to decide how to integrate the work | obra/superpowers |
| `fintel-data` | > | himself65/finance-skills |
| `free-tools` | When the user wants to plan or build a free tool as marketing, or asks whether a tool idea is worth building o… | coreyhaines31/marketingskills |
| `frontend-design` | Guidance for distinctive, intentional visual design when building new UI or reshaping an existing one. Helps w… | anthropics/skills |
| `generative-ui` | > | himself65/finance-skills |
| `graphify` | Use for any question about a codebase, its architecture, file relationships, or project content — especially w… | Graphify-Labs/graphify |
| `grill-me` | A relentless interview to sharpen a plan or design. | mattpocock/skills |
| `hallmark` | Design skill for websites and new pages that look designed, not generated. Use when the user asks to build or … | Nutlope/hallmark |
| `hormuz-strait` | > | himself65/finance-skills |
| `humanizer` | Rewrite AI-sounding text so it reads like the writer without changing what it says. Use when editing or review… | blader/humanizer |
| `hyperliquid-reader` | > | himself65/finance-skills |
| `image` | When the user wants to create, generate, edit, or optimize marketing images, or asks which approach to take (g… | coreyhaines31/marketingskills |
| `influencer-marketing` | When the user wants creator, influencer, or ambassador partnerships, or asks which creators fit, what to pay, … | coreyhaines31/marketingskills |
| `internal-comms` | A set of resources to help me write all kinds of internal communications, using the formats that my company li… | anthropics/skills |
| `json-canvas` | Create and edit JSON Canvas files (.canvas) with nodes, edges, groups, and connections. Use when working with … | obsidianmd/obsidian-skills |
| `kami` | Typeset professional documents with Kami templates: resumes, one-pagers, white papers, letters, portfolios, sl… | tw93/Kami |
| `karpathy-guidelines` | Behavioral guidelines to reduce common LLM coding mistakes. Use when writing, reviewing, or refactoring code t… | multica-ai/andrej-karpathy-skills |
| `knap` | Render Markdown from templates and structured data using Knap CLI. Use when the user asks to apply a Knap temp… | obsidianmd/obsidian-skills |
| `last30days` | Research what people actually say about any topic in the last 30 days. Pulls posts and engagement from Reddit,… | mvanhorn/last30days-skill |
| `launch` | When the user wants to plan a product or feature launch, or asks whether it's ready, when to announce, or how … | coreyhaines31/marketingskills |
| `lead-magnets` | When the user wants to plan or improve a lead magnet, or asks what to give away for emails or how much to ask … | coreyhaines31/marketingskills |
| `link-building` | When the user wants backlinks and mentions that lift rankings and AI citations, or asks how to get sites to li… | coreyhaines31/marketingskills |
| `linkedin-reader` | > | himself65/finance-skills |
| `marketing-council` | When the user wants several expert takes on a marketing decision, or asks what a famous marketer would say abo… | coreyhaines31/marketingskills |
| `marketing-ideas` | When the user wants marketing ideas or growth tactics for a software product, or asks what to try to get atten… | coreyhaines31/marketingskills |
| `marketing-loops` | When the user wants a recurring marketing job an AI agent runs on a cadence or trigger, or asks what a weekly … | coreyhaines31/marketingskills |
| `marketing-plan` | When the user wants a full marketing or go-to-market plan for a client, an advised company, or their own produ… | coreyhaines31/marketingskills |
| `marketing-psychology` | When the user wants to apply psychology to marketing, or asks why buyers behave or value things as they do, or… | coreyhaines31/marketingskills |
| `obsidian-bases` | Create and edit Obsidian Bases (.base files) with views, filters, formulas, and summaries. Use when working wi… | obsidianmd/obsidian-skills |
| `obsidian-cli` | Interact with Obsidian vaults using the Obsidian CLI to read, create, search, and manage notes, tasks, propert… | obsidianmd/obsidian-skills |
| `obsidian-headless` | Sync and publish Obsidian vaults from the command line with Obsidian Headless (`ob`), without the desktop app.… | obsidianmd/obsidian-skills |
| `obsidian-markdown` | Create and edit Obsidian Flavored Markdown with wikilinks, embeds, callouts, properties, and other Obsidian-sp… | obsidianmd/obsidian-skills |
| `offers` | When the user wants to design or improve the offer itself, or asks why it isn't selling or how to add urgency … | coreyhaines31/marketingskills |
| `onboarding` | When the user wants better onboarding and activation, or asks why new users don't stick or what the first sess… | coreyhaines31/marketingskills |
| `opencli-reader` | > | himself65/finance-skills |
| `options-payoff` | > | himself65/finance-skills |
| `paywalls` | When the user wants to create or improve in-app paywalls and upgrade moments, or asks when or how hard to ask … | coreyhaines31/marketingskills |
| `pdf` | Use this skill whenever the user wants to do anything with PDF files. This includes reading or extracting text… | anthropics/skills |
| `popups` | When the user wants to create or improve popups, modals, slide-ins, sticky bars, and banners, or asks whether … | coreyhaines31/marketingskills |
| `pptx` | Use this skill any time a .pptx or .potx file is involved in any way — as input, output, or both. This include… | anthropics/skills |
| `pricing` | When the user wants to set pricing and packaging, or asks what to charge, whether to raise prices, or how to m… | coreyhaines31/marketingskills |
| `product-marketing` | When the user wants to create or update the product marketing context doc (.agents/product-marketing.md), or a… | coreyhaines31/marketingskills |
| `programmatic-seo` | When the user wants SEO pages at scale from templates and data, or asks whether a page set will rank or look t… | coreyhaines31/marketingskills |
| `prospecting` | When the user wants to find and qualify prospects for outbound, or asks who to target first, which signal to p… | coreyhaines31/marketingskills |
| `public-relations` | When the user wants press and media coverage, or asks what to say to a reporter, whether a story is newsworthy… | coreyhaines31/marketingskills |
| `receiving-code-review` | Use when receiving code review feedback, before implementing suggestions, especially if feedback seems unclear… | obra/superpowers |
| `referrals` | When the user wants referral and affiliate programs or word of mouth, or asks what to reward, how much to pay,… | coreyhaines31/marketingskills |
| `requesting-code-review` | Use when completing tasks, implementing major features, or before merging to verify work meets requirements | obra/superpowers |
| `reverse-engineer-marketing` | When the user wants to know how another company grew and what to copy, or asks what a competitor did and when:… | coreyhaines31/marketingskills |
| `revops` | When the user wants to design revenue operations, or asks when a lead is ready for sales or why sales and mark… | coreyhaines31/marketingskills |
| `saas-valuation-compression` | > | himself65/finance-skills |
| `sales-enablement` | When the user wants sales collateral, or asks what to give a champion or rep, or how to answer an objection or… | coreyhaines31/marketingskills |
| `schema` | When the user wants to add, fix, or validate schema markup (JSON-LD), or asks which type fits a page or whethe… | coreyhaines31/marketingskills |
| `seo-audit` | When the user wants to audit or diagnose SEO, or asks why traffic dropped, a page won't rank, or whether a set… | coreyhaines31/marketingskills |
| `sepa-strategy` | > | himself65/finance-skills |
| `signup` | When the user wants better signup, registration, and trial start flows, or asks which fields or steps to cut o… | coreyhaines31/marketingskills |
| `site-architecture` | When the user wants to plan or restructure a website, or asks which pages they need or where something belongs… | coreyhaines31/marketingskills |
| `skill-creator` | Create new skills, modify and improve existing skills, and measure skill performance. Use when users want to c… | anthropics/skills |
| `slides` | Create strategic HTML presentations with Chart.js, design tokens, responsive layouts, copywriting formulas, an… | nextlevelbuilder/ui-ux-pro-max-skill |
| `sms` | When the user wants SMS, MMS, or WhatsApp marketing, or asks whether texting is worth it or a message is allow… | coreyhaines31/marketingskills |
| `social` | When the user wants organic social content for LinkedIn, X, Instagram, TikTok, or Facebook, or asks what to po… | coreyhaines31/marketingskills |
| `startup-analysis` | > | himself65/finance-skills |
| `stock-correlation` | > | himself65/finance-skills |
| `stock-liquidity` | > | himself65/finance-skills |
| `subagent-driven-development` | Use when executing implementation plans with independent tasks in the current session | obra/superpowers |
| `systematic-debugging` | Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes | obra/superpowers |
| `telegram-reader` | > | himself65/finance-skills |
| `test-driven-development` | Use when implementing any feature or bugfix, before writing implementation code | obra/superpowers |
| `theme-factory` | Toolkit for styling artifacts with a theme. These artifacts can be slides, docs, reportings, HTML landing page… | anthropics/skills |
| `tradingview-mcp` | > | himself65/finance-skills |
| `tradingview-reader` | > | himself65/finance-skills |
| `twitter-reader` | > | himself65/finance-skills |
| `ui-styling` | Create beautiful, accessible user interfaces with shadcn/ui components (built on Radix UI + Tailwind), Tailwin… | nextlevelbuilder/ui-ux-pro-max-skill |
| `ui-ux-pro-max` | UI/UX design intelligence for web, mobile, and desktop. This skill should be used when designing, building, re… | nextlevelbuilder/ui-ux-pro-max-skill |
| `ultracave` | Caveman at maximum compression: fragments, one word when one word is enough, each fact once. Invoke only with … | JuliusBrussee/caveman |
| `using-git-worktrees` | Use when starting feature work that needs isolation from current workspace or before executing implementation … | obra/superpowers |
| `using-superpowers` | Use when starting any conversation - establishes how to find and use skills, requiring skill invocation before… | obra/superpowers |
| `verification-before-completion` | Use when about to claim work is complete, fixed, or passing, before committing or creating PRs - requires runn… | obra/superpowers |
| `video` | When the user wants to create video with AI tools or code, or asks which approach to use (screen recording, AI… | coreyhaines31/marketingskills |
| `writing-plans` | Use when you have a spec or requirements for a multi-step task, before touching code | obra/superpowers |
| `writing-skills` | Use when creating new skills, editing existing skills, or verifying skills work before deployment | obra/superpowers |
| `xlsx` | Use this skill any time a spreadsheet file is the primary input or output. This means any task where the user … | anthropics/skills |
| `yc-reader` | > | himself65/finance-skills |
| `yfinance-data` | > | himself65/finance-skills |
