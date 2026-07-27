# Professional Review — Initial Pass

## Fixed in this version

1. Removed three conflicting `student_dashboard` view definitions and kept one authenticated, data-driven implementation.
2. Prevented users from opening sections that do not belong to their own exam attempt.
3. Prevented editing completed attempts and viewing incomplete results.
4. Recorded `submitted_at` when the final section is submitted, fixing average-time calculations.
5. Preserved the latest attempt per exam instead of accidentally overwriting it with an older one.
6. Validated the exam-list status filter.
7. Removed duplicate `Section.__str__` code.
8. Removed duplicate CSS/CDN imports and references to missing static files.
9. Moved secret key, debug mode, and hosts toward environment-based configuration.
10. Changed the project timezone to `Asia/Tashkent` and login redirect to the student dashboard.
11. Added `requirements.txt`, `.env.example`, and setup documentation.
12. Removed accidental Microsoft Word support folders from template directories.

## Important remaining work

### Priority 1 — Core exam reliability
- Add database constraints to prevent duplicate answers and duplicate active attempts.
- Add proper section/question ordering fields and navigation state.
- Save answers periodically so refreshes do not erase work.
- Store server-side exam deadlines; the current JavaScript-only timer can be bypassed.
- Add validation for required questions and malformed JSON options.
- Build robust IELTS scoring conversion instead of displaying only raw correct counts.

### Priority 2 — Exam builder
- Create staff-only exam builder pages instead of relying solely on Django admin.
- Support bulk question and answer import.
- Add passage, audio, question-group, and preview workflows.
- Support IELTS question types separately: true/false/not given, headings, sentence completion, maps, multiple selection, etc.

### Priority 3 — Product UI
- Consolidate Bootstrap and Tailwind into one deliberate frontend system.
- Replace placeholder dashboard values with real metrics.
- Add responsive mobile navigation and accessible form states.
- Create consistent empty, loading, success, and error states.

### Priority 4 — Deployment
- Use PostgreSQL in production.
- Configure secure cookies, HTTPS redirect, CSRF trusted origins, email delivery, and media storage.
- Add automated tests and a deployment pipeline.
- Never upload virtual environments, `db.sqlite3`, `.env`, or collected `staticfiles` to Git.
