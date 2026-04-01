# PyLearn — Code Review v2 (March 14, 2026)

## Bugs Found

1. **`safe_slot` decorator doesn't return values** (`error_handler.py:152`) — wrapped function returns None. Low impact (most Qt slots don't return values), but technically broken.
2. **Race condition in Session.run() output reading** (`session.py:193-199`) — two threads read stdout/stderr with join(timeout). If first thread times out, second gets wrong remaining time. Fragile.
3. **Color validation regex too loose** (`output_handler.py:64`) — accepts invalid hex like `#xyz`. Falls back to #888, but sloppy.
4. **Database rollback swallows errors silently** (`database.py:67-69`) — rollback failure leaves connection in unknown state. No logging of original error.
5. **TestRunner parse logic is confusing** (`test_runner.py:95-99`) — `if tests else setup_block` condition is unreachable. Setup prepended correctly but fallback is dead code.

## Code Smells

- [ ] **Database connection "fire and forget"** — `MainWindow.__init__()` opens persistent connection, only closes on app exit. Exception during init = leaked connection.
- [ ] **Duplicate test execution logic** — ChallengePanel and ProjectPanel both create identical `_TestWorker` threads. Should be a shared utility.
- [ ] **No JSON schema validation** — ContentLoader accepts any dict. Malformed quiz JSON gives generic errors.
- [ ] **Subprocess environment sanitization incomplete** — strips sensitive vars but doesn't prevent PATH manipulation.
- [ ] **No batch operations in delete** — `reset_quiz_progress()` loops individual DELETEs instead of single `DELETE WHERE IN`.

## Test Gaps

- [ ] PDF parsing edge cases (corrupted PDFs, password-protected, negative font sizes) — 16% coverage
- [ ] Database transaction failures (locked DB, disk full, corruption)
- [ ] ContentLoader with malformed/missing JSON
- [ ] Session output truncation at 2MB boundary
- [ ] UI memory leak detection (QThread worker cleanup)
- [ ] Full learning flow integration (load book → quiz → challenge → project step)

## Honest Assessment

**What's genuinely good:**
- Database layer (clean schema, ON CONFLICT, indexes, N+1 fixes)
- Error handling infrastructure (@safe_slot, global exception handler, logging)
- Executor design (persistent subprocess session, timeout with process tree kill)
- Type safety (mypy strict on core code)
- Code organization (clear separation of concerns)

**What's just fine:**
- UI implementation (follows Qt patterns, but panels have duplication)
- Testing (79% decent, but gaps in PDF/DB edge cases and UI lifecycle)
- Content system (reads JSON, but no schema validation or batch ops)

**What's weak:**
- Subprocess management is Windows-specific (taskkill), fragile on Linux
- Error messages are generic ("Parsing failed", "Execution error")
- Internal API documentation is sparse

## Rating: 7.5/10

Solid indie desktop app. Past hobby project stage — on PyPI, has CI, professional error handling. Not commercial SaaS grade (no analytics, telemetry, migration system). Competitive differentiator: reading a real PDF textbook side-by-side with live code editor + integrated quizzes. That's genuinely unique.

## Priority Fixes

1. Fix `safe_slot` return value (minutes)
2. Add JSON schema validation to ContentLoader (hours)
3. Add logging to database transaction failures (hours)
4. Extract shared test execution utility (half day)
5. Expand PDF parser test coverage (days)
