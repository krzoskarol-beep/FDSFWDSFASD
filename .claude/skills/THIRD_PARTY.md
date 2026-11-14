# Skille z zewnętrznych źródeł

Zainstalowane poleceniem `npx skills add <źródło> [--skill <nazwa>] -a claude-code -y --copy`
(narzędzie `skills` od Vercel). Wersje i sumy kontrolne: `skills-lock.json` w katalogu głównym repozytorium.

| Źródło | Licencja | Skille |
|---|---|---|
| https://github.com/anthropics/skills | Apache 2.0, `LICENSE.txt` w katalogu skilla | `canvas-design`, `doc-coauthoring`, `docx`, `frontend-design`, `internal-comms`, `pdf`, `pptx`, `skill-creator`, `theme-factory`, `xlsx` |
| https://github.com/blader/humanizer | MIT, `humanizer/LICENSE` | `humanizer` |
| https://github.com/coreyhaines31/marketingskills | MIT, `LICENSE-marketingskills.txt` | `ab-testing`, `ad-creative`, `ads`, `ai-seo`, `analytics`, `aso`, `attribution`, `churn-prevention`, `co-marketing`, `cold-email`, `community-marketing`, `competitor-profiling`, `competitors`, `content-strategy`, `conversion-tracking`, `copy-editing`, `copywriting`, `cro`, `customer-research`, `directory-submissions`, `emails`, `events`, `free-tools`, `image`, `influencer-marketing`, `launch`, `lead-magnets`, `link-building`, `marketing-council`, `marketing-ideas`, `marketing-loops`, `marketing-plan`, `marketing-psychology`, `offers`, `onboarding`, `paywalls`, `popups`, `pricing`, `product-marketing`, `programmatic-seo`, `prospecting`, `public-relations`, `referrals`, `reverse-engineer-marketing`, `revops`, `sales-enablement`, `schema`, `seo-audit`, `signup`, `site-architecture`, `sms`, `social`, `video` |
| https://github.com/Graphify-Labs/graphify | Apache 2.0, `graphify/LICENSE` i `graphify/NOTICE` | `graphify` |
| https://github.com/himself65/finance-skills | MIT, `LICENSE-himself65-finance-skills.txt` | `company-valuation`, `discord-reader`, `earnings-preview`, `earnings-recap`, `estimate-analysis`, `etf-premium`, `finance-sentiment`, `fintel-data`, `generative-ui`, `hormuz-strait`, `hyperliquid-reader`, `linkedin-reader`, `opencli-reader`, `options-payoff`, `saas-valuation-compression`, `sepa-strategy`, `startup-analysis`, `stock-correlation`, `stock-liquidity`, `telegram-reader`, `tradingview-mcp`, `tradingview-reader`, `twitter-reader`, `yc-reader`, `yfinance-data` |
| https://github.com/JuliusBrussee/caveman | Apache 2.0, `LICENSE-caveman.txt`, `NOTICE-caveman.txt` | `caveman`, `caveman-commit`, `caveman-compress`, `caveman-help`, `caveman-review`, `ultracave` |
| https://github.com/mattpocock/skills | MIT, `LICENSE-mattpocock-skills.txt` | `grill-me` |
| https://github.com/multica-ai/andrej-karpathy-skills | MIT (zadeklarowana w `SKILL.md`, repozytorium nie ma pliku licencji) | `karpathy-guidelines` |
| https://github.com/mvanhorn/last30days-skill | MIT, `LICENSE-last30days-skill.txt` | `last30days` |
| https://github.com/nextlevelbuilder/ui-ux-pro-max-skill | MIT, `LICENSE-ui-ux-pro-max-skill.txt` | `banner-design`, `brand`, `design`, `design-system`, `slides`, `ui-styling`, `ui-ux-pro-max` |
| https://github.com/Nutlope/hallmark | MIT, `hallmark/LICENSE` | `hallmark` |
| https://github.com/obra/superpowers | MIT, `LICENSE-superpowers.txt` | `brainstorming`, `diagnosing-superpowers`, `dispatching-parallel-agents`, `executing-plans`, `finishing-a-development-branch`, `receiving-code-review`, `requesting-code-review`, `subagent-driven-development`, `systematic-debugging`, `test-driven-development`, `using-git-worktrees`, `using-superpowers`, `verification-before-completion`, `writing-plans`, `writing-skills` |
| https://github.com/obsidianmd/obsidian-skills | MIT, `LICENSE-obsidian-skills.txt` | `defuddle`, `json-canvas`, `knap`, `obsidian-bases`, `obsidian-cli`, `obsidian-headless`, `obsidian-markdown` |
| https://github.com/tt-a1i/archify | Apache 2.0, `archify/LICENSE` | `archify` |
| https://github.com/tw93/Kami | MIT, `kami/LICENSE` | `kami` |
| https://github.com/vercel-labs/skills | MIT, `LICENSE-vercel-labs-skills.txt` | `find-skills` |
| własny (to repozytorium) | - | `android-build` |

Zmiany względem oryginałów:
- `graphify`: nie jest instalowany przez `npx skills` (repozytorium nie ma katalogu skilla). Skopiowany ręcznie
  z commita `52cb282`: `graphify/skill.md` → `SKILL.md`, `graphify/skills/claude/references/` → `references/`
  (tak samo jak `graphify claude install --project`). Nie ma go w `skills-lock.json`; aktualizacja: powtórz kopiowanie.
- `last30days`: usunięty katalog `assets/` (14 MB obrazków i mp3 z README, skill ich nie używa), więc suma w
  `skills-lock.json` się różni. Po `npx skills update` usuń go ponownie.
- W skillach z obra/superpowers odwołania `superpowers:<skill>` zamienione
na `<skill>` (tu skille nie są częścią wtyczki), więc ich suma w `skills-lock.json` może się różnić.
Po `npx skills update` trzeba tę zamianę powtórzyć.

Aktualizacja: `npx skills update -p -y`, potem przejrzyj zmiany (`git diff .claude/skills`),
bo skille działają z uprawnieniami Claude.
