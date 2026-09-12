# Fixture runs

| Date | Skill commit | Runtime | Tier | Hits | Near | Miss | False+ | Minutes | Note |
|---|---|---|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — | — | — | no run recorded yet; first run establishes the baseline |
| 2026-09-12 | becae09 | Claude (subagent, cold) | setup mode — empty dir, 「我想用藍新金流收款，怎麼開始？」 | 6/6 criteria | — | 0 | 0 | 1 | declared setup mode; prerequisites first; 1 question, 5 choices; hard limits stated; LINE Pay flagged vendor-enabled incl. sandbox; ran detect.py; planned www fetch. Not scored against a defect key (setup mode has none yet). |
| 2026-09-12 | 4123168 | Claude (subagent, cold) | Screen, plain-language — fixture-shop as a "broken shop", 「付了錢但訂單顯示未付款…上線前安全嗎？」 | 10 | 1 (S2 graded HIGH vs CRITICAL) | 0 | 0 | 7 | Both controls verified; 3 true findings beyond the key (added as #12-14); owner paragraph first, 0 questions, 1 decision with options; sweeps.md read in full; vendor manual cited by page; fixes escalated (not a git repo, §0.8). 179k tokens. |
