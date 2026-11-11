# Skille z zewnętrznych źródeł

Zainstalowane poleceniem `npx skills add <źródło> [--skill <nazwa>] -a claude-code -y --copy`
(narzędzie `skills` od Vercel). Wersje i sumy kontrolne: `skills-lock.json` w katalogu głównym repozytorium.

| Źródło | Licencja | Skille |
|---|---|---|
| https://github.com/anthropics/skills | Apache 2.0, `LICENSE.txt` w katalogu skilla | `canvas-design`, `doc-coauthoring`, `docx`, `frontend-design`, `internal-comms`, `pdf`, `pptx`, `theme-factory`, `xlsx` |
| https://github.com/himself65/finance-skills | MIT, `LICENSE-himself65-finance-skills.txt` | `company-valuation`, `discord-reader`, `earnings-preview`, `earnings-recap`, `estimate-analysis`, `etf-premium`, `finance-sentiment`, `fintel-data`, `generative-ui`, `hormuz-strait`, `hyperliquid-reader`, `linkedin-reader`, `opencli-reader`, `options-payoff`, `saas-valuation-compression`, `sepa-strategy`, `skill-creator`, `startup-analysis`, `stock-correlation`, `stock-liquidity`, `telegram-reader`, `tradingview-mcp`, `tradingview-reader`, `twitter-reader`, `yc-reader`, `yfinance-data` |
| https://github.com/mattpocock/skills | MIT, `LICENSE-mattpocock-skills.txt` | `grill-me` |
| https://github.com/obra/superpowers | MIT, `LICENSE-superpowers.txt` | `brainstorming`, `diagnosing-superpowers`, `dispatching-parallel-agents`, `executing-plans`, `finishing-a-development-branch`, `receiving-code-review`, `requesting-code-review`, `subagent-driven-development`, `systematic-debugging`, `test-driven-development`, `using-git-worktrees`, `using-superpowers`, `verification-before-completion`, `writing-plans`, `writing-skills` |
| https://github.com/tw93/Kami | MIT, `kami/LICENSE` | `kami` |
| https://github.com/vercel-labs/skills | MIT, `LICENSE-vercel-labs-skills.txt` | `find-skills` |
| własny (to repozytorium) | - | `android-build` |

Zmiany względem oryginałów: w skillach z obra/superpowers odwołania `superpowers:<skill>` zamienione
na `<skill>` (tu skille nie są częścią wtyczki), więc ich suma w `skills-lock.json` może się różnić.
Po `npx skills update` trzeba tę zamianę powtórzyć.

Aktualizacja: `npx skills update -p -y`, potem przejrzyj zmiany (`git diff .claude/skills`),
bo skille działają z uprawnieniami Claude.
