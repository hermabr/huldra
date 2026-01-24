# Executor implementation — Ralph loop entrypoint

You are running in a Ralph Wiggum loop using OpenCode.
This prompt will be repeated across iterations.

## Context (read first)
- plans/executor/plan.md
- plans/executor-plan/00-index.md
- All unfinished files under plans/executor-plan/

These documents are the source of truth.

## Repository state assumptions
- You are already on the correct feature branch.
- The branch should be pushed to origin.
- Do NOT create or switch branches.
- Do NOT use git hooks.

## Rules (follow strictly)

### Implementation
1. Identify the next unfinished checklist item in the plan.
2. Implement the smallest coherent unit of work.
3. Update the relevant plan file(s):
   - mark completed checkboxes
   - add a short progress note

### Verification
4. Run:
   - `make test`
5. Fix failures before proceeding.

### Git discipline (IMPORTANT)
6. If there are code or plan changes and tests pass:
   - `git status --porcelain` must show only intended files
   - Commit with a concise message:
     - prefix with the plan section (e.g. `executor:`, `planner:`)
   - Push:
     - `git push origin HEAD`

You must do the commit AND the push yourself.

### Pull request creation
7. When ALL plan tasks are complete and tests pass:
   - Create a pull request using GitHub CLI:
     ```
     gh pr create \
       --base main \
       --head $(git branch --show-current) \
       --title "Executor v1: local + slurm execution" \
       --body "Implements executor plan under plans/executor-plan/"
     ```
   - If the PR already exists, do NOT create a duplicate.

### Stop condition
Only when:
- all plan checklists are complete
- tests pass
- changes are committed and pushed
- PR exists

Output **exactly**:

<promise>COMPLETE</promise>
