---
name: speckit.tasks
description: (Step 3) Generate an actionable, dependency-ordered tasks.md for the feature based on available design artifacts.
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

1. **Setup**: Run `scripts/check-prerequisites.sh --json` from repo root and parse FEATURE_DIR and AVAILABLE_DOCS list. All paths must be absolute. For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").

2. **Load design documents**: Read from FEATURE_DIR:
   - **Required**: plan.md (tech stack, libraries, structure), spec.md (user stories with priorities)
   - **Optional**: data-model.md (entities), contracts/ (API endpoints), research.md (decisions), quickstart.md (test scenarios)
   - **Test context** (if test-registry.json exists):
     - Run `scripts/test-registry.sh spec <number> --json` from repo root (where <number> is spec number from FEATURE_DIR)
     - Parse JSON output to identify existing tests for this spec
     - Use to avoid duplicate test tasks
     - **Retirement workflow** (for migration/refactoring specs):
       - Run `scripts/test-registry.sh retire --filter <tag> --json` to find tests marked for retirement
       - Common filters: `mockDependent` (Tauri migration), `slow` (performance work), `contractTest` (API changes)
       - Generate retirement tasks BEFORE new implementation tasks (clean up deprecated tests first)
       - Example: `- [ ] T005 [P] Retire mock-dependent workspace tests (3 tests)`
       - Include specific test file paths from retire command output
   - Note: Not all projects have all documents. Generate tasks based on what's available.

3. **Execute task generation workflow**:
   - Load plan.md and extract tech stack, libraries, project structure
   - Load spec.md and extract user stories with their priorities (P1, P2, P3, etc.)
   - If data-model.md exists: Extract entities and map to user stories
   - If contracts/ exists: Map endpoints to user stories
   - If research.md exists: Extract decisions for setup tasks
   - Generate tasks organized by user story (see Task Generation Rules below)
   - Generate dependency graph showing user story completion order
   - Create parallel execution examples per user story
   - Validate task completeness (each user story has all needed tasks, independently testable)

4. **Generate tasks.md**: Use `assets/tasks-template.md` as structure, fill with:
   - Correct feature name from plan.md
   - Phase 1: Setup tasks (project initialization)
   - Phase 2: Foundational tasks (blocking prerequisites for all user stories)
   - Phase 3+: One phase per user story (in priority order from spec.md)
   - Each phase includes: story goal, independent test criteria, tests (if requested), implementation tasks
   - Final Phase: Polish & cross-cutting concerns
   - All tasks must follow the strict checklist format (see Task Generation Rules below)
   - Clear file paths for each task
   - Dependencies section showing story completion order
   - Parallel execution examples per story
   - Implementation strategy section (MVP first, incremental delivery)

5. **Report**: Output path to generated tasks.md and summary:
   - Total task count
   - Task count per user story
   - Parallel opportunities identified
   - Independent test criteria for each story
   - Suggested MVP scope (typically just User Story 1)
   - Format validation: Confirm ALL tasks follow the checklist format (checkbox, ID, labels, file paths)

Context for task generation: $ARGUMENTS

The tasks.md should be immediately executable - each task must be specific enough that an LLM can complete it without additional context.

## Task Generation Rules

**CRITICAL**: Tasks MUST be organized by user story to enable independent implementation and testing.

**Tests are OPTIONAL**: Only generate test tasks if explicitly requested in the feature specification or if user requests TDD approach.

### Checklist Format (REQUIRED)

Every task MUST strictly follow this format:

```text
- [ ] [TaskID] [P?] [Story?] Description with file path
```

**Format Components**:

1. **Checkbox**: ALWAYS start with `- [ ]` (markdown checkbox)
2. **Task ID**: Sequential number (T001, T002, T003...) in execution order
3. **[P] marker**: Include ONLY if task is parallelizable (different files, no dependencies on incomplete tasks)
4. **[Story] label**: REQUIRED for user story phase tasks only
   - Format: [US1], [US2], [US3], etc. (maps to user stories from spec.md)
   - Setup phase: NO story label
   - Foundational phase: NO story label  
   - User Story phases: MUST have story label
   - Polish phase: NO story label
5. **Description**: Clear action with exact file path

**Examples**:

- ✅ CORRECT: `- [ ] T001 Create project structure per implementation plan`
- ✅ CORRECT: `- [ ] T005 [P] Implement authentication middleware in src/middleware/auth.py`
- ✅ CORRECT: `- [ ] T012 [P] [US1] Create User model in src/models/user.py`
- ✅ CORRECT: `- [ ] T014 [US1] Implement UserService in src/services/user_service.py`
- ❌ WRONG: `- [ ] Create User model` (missing ID and Story label)
- ❌ WRONG: `T001 [US1] Create model` (missing checkbox)
- ❌ WRONG: `- [ ] [US1] Create User model` (missing Task ID)
- ❌ WRONG: `- [ ] T001 [US1] Create model` (missing file path)

### Task Organization

1. **From User Stories (spec.md)** - PRIMARY ORGANIZATION:
   - Each user story (P1, P2, P3...) gets its own phase
   - Map all related components to their story:
     - Models needed for that story
     - Services needed for that story
     - Endpoints/UI needed for that story
     - If tests requested: Tests specific to that story
   - Mark story dependencies (most stories should be independent)
   
2. **From Contracts**:
   - Map each contract/endpoint → to the user story it serves
   - If tests requested: Each contract → contract test task [P] before implementation in that story's phase
   
3. **From Data Model**:
   - Map each entity to the user story(ies) that need it
   - If entity serves multiple stories: Put in earliest story or Setup phase
   - Relationships → service layer tasks in appropriate story phase
   
4. **From Setup/Infrastructure**:
   - Shared infrastructure → Setup phase (Phase 1)
   - Foundational/blocking tasks → Foundational phase (Phase 2)
   - Story-specific setup → within that story's phase

5. **From Test Registry (Retirement)**:
   - Use `retire --filter <tag>` to identify tests for cleanup
   - Retirement tasks go in the phase that makes them obsolete
   - Examples:
     - Tauri migration spec: `retire --filter mockDependent` → retire mock API tests after real backend implemented
     - Performance spec: `retire --filter slow` → retire/optimize slow tests after optimization
     - API refactor spec: `retire --filter contractTest` → retire old contract tests after API changed
   - Task format: `- [ ] T015 [P] Retire 3 mock-dependent tests in src/__tests__/workspace.test.tsx`

### Phase Structure

- **Phase 1**: Setup (project initialization)
- **Phase 2**: Foundational (blocking prerequisites - MUST complete before user stories)
- **Phase 3+**: User Stories in priority order (P1, P2, P3...)
  - Within each story: Tests (if requested) → Models → Services → Endpoints → Integration → Retirement (if applicable)
  - Each phase should be a complete, independently testable increment
  - Retirement tasks placed AFTER new implementation (clean up once replacement works)
- **Final Phase**: Polish & Cross-Cutting Concerns

### Test Task Guidelines

**When tests ARE requested** (via spec or TDD approach), follow test pyramid targets:

- **Target Distribution**: 70% unit, 20% integration, 10% e2e
- **Per User Story**: Calculate expected test counts based on story complexity
- **Task Examples**:
  - Unit tests: `- [ ] T020 [P] [US1] Unit tests for UserService in tests/unit/test_user_service.py`
  - Integration tests: `- [ ] T035 [US2] Integration tests for auth flow in tests/integration/test_auth.py`
  - E2E tests: `- [ ] T045 [US3] E2E test for checkout flow in tests/e2e/test_checkout.py`

**Pyramid Health Considerations**:
- Use test registry data (from step 2) to understand current pyramid state
- If pyramid is inverted (WARN status): Prioritize unit test tasks
- Avoid generating excessive e2e tests (should be <10% of total)
- Focus e2e tests on critical user journeys only

**Test Task Placement**:
- Unit tests: Early in story phase (enable TDD)
- Integration tests: After unit tests, before full integration
- E2E tests: Near end of story phase (validate complete flow)
