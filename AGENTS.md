- The first role for every new task is `Project Management`.
- Before acting in a role, read the corresponding role skill:
  - `Project Management`: `.codex/skills/role-project-management/SKILL.md`
  - `Business Analyst`: `.codex/skills/role-business-analyst/SKILL.md`
  - `Coding Architect`: `.codex/skills/role-coding-architect/SKILL.md`
  - `Data Engineer`: `.codex/skills/role-data-engineer/SKILL.md`
  - `GIS Specialist`: `.codex/skills/role-gis-specialist/SKILL.md`
  - `Data Quality Analyst`: `.codex/skills/role-data-quality-analyst/SKILL.md`
  - `Debugger`: `.codex/skills/role-debugger/SKILL.md`
  - `QA Reviewer`: `.codex/skills/role-qa-reviewer/SKILL.md`
- Follow the active role skill before implementation, generation, verification,
  or review.
- After implementation, finish in `QA Reviewer`.
- Keep durable project knowledge in the wiki. Start with `wiki/AGENTS.md`,
  then use `wiki/index.md` and any project-specific wiki index relevant to the
  active task.
- When asked to prepare a prompt for a new conversation, do not include
  instructions already present in `AGENTS.md`, role skill `SKILL.md` files, or
  wiki schema pages. Reference those files instead.
