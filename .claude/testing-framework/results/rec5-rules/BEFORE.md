# Recommendation 5: Code Quality Rules - BEFORE Test

## Test Configuration
- **Date:** 2025-01-15
- **Test Prompt:** "Add error handling to the vehicle exit function"
- **Enhancement Applied:** NO (baseline test)

---

## Current State

### Configuration
No `.claude/rules/` directory exists. Code quality guidelines exist only in CLAUDE.md files, which I may or may not reference depending on context.

### Current Guidelines Location
- `CLAUDE.md` - Project overview and commit conventions
- `backend/CLAUDE.md` - Django patterns, service layer rules
- `frontend/CLAUDE.md` - Vue patterns, TypeScript rules

The issue: These files contain guidelines, but they're not explicitly loaded as **rules** that I must follow.

---

## Test Execution: Without Rules

### Scenario: Adding Error Handling

**Prompt:** "Add error handling to the vehicle exit function"

**My Behavior Without Rules:**
1. Read the function
2. Add error handling based on my general knowledge
3. May or may not follow MTT conventions

### Potential Issues

| Area | Risk | Current Protection |
|------|------|-------------------|
| Exception types | Might use generic `Exception` | Only CLAUDE.md guidance |
| Error messages | Might use English | CLAUDE.md says Russian |
| Service layer | Might add logic to view | CLAUDE.md says service layer |
| Response format | Might not use standard format | CLAUDE.md documents format |

### Simulated Output (Without Rules)

```python
@action(detail=False, methods=["post"], url_path="exit")
def exit_vehicle(self, request):
    try:
        # ... existing code ...
    except Exception as e:
        return Response(
            {"error": str(e)},  # ❌ Not standard format
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
```

**Problems:**
- Uses generic `Exception` instead of custom exceptions
- Error message in English (should be Russian)
- Response format doesn't match `{"success": false, "error": {...}}`
- Logic added to view instead of service

---

## Quality Metrics (BEFORE)

| Metric | Score | Rationale |
|--------|-------|-----------|
| Convention Compliance | 5/10 | Depends on if I read CLAUDE.md |
| Error Format | 4/10 | May not use standard format |
| Language Consistency | 4/10 | May forget Russian requirement |
| Architecture | 5/10 | May add logic to view |

**Overall BEFORE Score: 4.5/10**

---

## Expected Improvement with Rules

A rules file would:
1. ALWAYS be loaded and enforced
2. Define error handling patterns
3. Specify response format requirements
4. Enforce service layer pattern
5. Set language requirements
