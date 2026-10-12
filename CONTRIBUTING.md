# Contributing

HydrantWorks works like a small team's service: nothing reaches `main`
without a pull request and a green CI run.

## The flow

1. **Start from an issue.** Every change answers one issue. If there isn't one,
   write it first: what is wrong or missing, and how you will know it is done.
2. **Branch** from an up-to-date `main`: `fix/12-jurisdiction-case` or
   `feat/14-nearby-hydrants`.
3. **Write or change a test first** that fails for the reason in the issue.
4. **Make the change.** Keep it to the issue. A refactor you want to do along
   the way is its own issue.
5. **Run what CI runs** (PowerShell, in the repo folder, virtual environment active):
   ```powershell
   ruff check .
   pytest
   ```
6. **Open a pull request** and fill in the template, including the
   AI-assistance section.
7. **Get a review.** Address every comment, either with a change or with a reply
   explaining why not.

## Conventions

- All SQL lives in `hydrantworks/repository.py`.
- Request and response shapes live in `hydrantworks/models.py`; a change there
  is a change to the API contract, so call it out in the pull request.
- Every write goes through a repository function that also writes an audit row.
- Times are stored in UTC.
- Do not commit `.env`, `*.db`, or anything under `logs/`.

## AI assistance

Using coding agents and assistants is expected. Disclosing it is required: in
the pull request, say which tools you used, for what, and what you checked
yourself. You must be able to explain every line you submit.
