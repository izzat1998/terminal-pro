# MTT Workflow Rules

These rules govern HOW Claude approaches tasks, not what code to write.

## Rule 1: Plan Before Building

**MUST:** Always outline an approach before writing implementation code.

When asked to create a feature, fix a bug, or build anything non-trivial:
1. Read relevant files to understand the current state
2. Present a brief plan (3-5 bullet points) showing:
   - What files will be changed
   - What the approach is
   - Any edge cases or risks identified
3. Wait for user approval before writing code

**Exception:** Single-line fixes, typos, or when the user says "just do it" / provides very specific instructions.

**WRONG:**
```
User: "Add billing export feature"
Claude: *immediately starts writing code across 6 files*
```

**CORRECT:**
```
User: "Add billing export feature"
Claude: "Here's my plan:
  - Add export endpoint in billing/views.py
  - Create export_service.py for Excel generation
  - Add frontend button in MonthlyStatements.vue
  Edge cases: large datasets, concurrent exports, auth for downloads"
User: "Looks good, proceed"
Claude: *now writes code*
```

---

## Rule 2: Enumerate Edge Cases for Business Logic

**MUST:** Before implementing financial, billing, or state-management logic, explicitly list edge cases.

Always consider:
- **Float precision** - Use `Decimal`, never `float` for money
- **Free days / grace periods** - Containers with 0-cost initial period
- **Backdating** - What if dates are in the past?
- **Race conditions** - Concurrent requests modifying same record
- **Immutability** - Historical records must not change after billing
- **State transitions** - Which transitions are valid? (e.g., can an exited container re-enter?)
- **Empty/null data** - What if required fields are missing?
- **Boundary values** - Month boundaries, year boundaries, timezone edges

Present these to the user before implementing.

---

## Rule 3: Git Workflow

**MUST:** Follow these git practices:

1. Before committing, run `git status` and `git diff` to review what will be committed
2. Report what was committed with commit hashes
3. Do NOT re-commit already-pushed changes
4. Do NOT push unless explicitly asked
5. Separate backend/frontend/test changes into logical commits when they're independent
6. Follow conventional commit format from CLAUDE.md

---

## Rule 4: Use Requested Skills

**MUST:** When the user asks to use a specific skill (e.g., "use playground skill", "use brainstorming"), invoke that skill immediately.

Do NOT:
- Proceed with an alternative approach without the skill
- Start building without the skill if one was requested
- Partially follow a skill's workflow

---

## Rule 5: Verify Dependencies

**MUST:** When adding new imports or dependencies:

**Python (backend):**
- Check if the package is in `backend/requirements.txt`
- If not, add it and note that `pip install -r requirements.txt` is needed

**TypeScript/JavaScript (frontend, telegram-miniapp):**
- Check if the package is in `package.json`
- If not, note that `npm install <package>` is needed

Never assume a package is installed. Verify first.

---

## Rule 6: Running the Project

When asked to "run the project" or "start dev", use:
```bash
make dev
```

This starts all three services (backend:8008, frontend:5174, telegram-miniapp:5175).

For individual services:
```bash
make backend           # Django on port 8008
make frontend          # Vue on port 5174
make telegram-miniapp  # React Telegram Mini App on port 5175
```

After starting, verify services are running by checking their health endpoints or logs.
If a service fails to start, check for:
- Missing dependencies (run `make install`)
- Pending migrations (run `make migrate`)
- Port conflicts
- Missing `.env` file
