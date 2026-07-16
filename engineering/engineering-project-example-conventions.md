---
name: Project Example Conventions
description: Example project conventions agent — replace this with your own project's rules. Apply these conventions whenever working in the {{PROJECT_REPO}} project.
color: gray
emoji: 📋
---

# Project Example Conventions

Apply these rules whenever working in the `{{PROJECT_REPO}}` project. This file is a starting template — replace the examples below with your own project's actual conventions.

---

## 1. Module Architecture

```
my-app/
├── app/              # Main app module — UI, ViewModels, features
├── models/           # Serializable domain models (no platform dependency)
├── data/             # Repository implementations, remote/local data sources
├── core/
│   ├── database/     # DAOs, Room entities, TypeConverters
│   ├── network/      # API clients, error handling
│   └── utils/        # Shared utilities and extensions
└── ui/
    └── res/          # String resources, shared UI helpers
```

### Where to put new code

| Type | Location |
|---|---|
| Domain model (no platform dep) | `:models` |
| Room DAO / Entity | `:core:database` |
| API client / response model | `:core:network` |
| Shared utility / extension | `:core:utils` |
| Feature ViewModel | `:app` (feature package) |
| Feature UI / Screen | `:app` (feature package) |

---

## 2. Coding Conventions

### Naming

- **Files / Classes**: UpperCamelCase. Android component subclasses end with the component name (e.g. `SignInActivity`, `UserProfileFragment`).
- **Resource files**: lowercase_underscore (e.g. `activity_sign_in.xml`, `ic_arrow_back.png`).
- **Constants prefix by context**: SharedPreferences → `PREF_`, Bundle → `BUNDLE_`, Intent extras → `EXTRA_`, Fragment args → `ARG_`.
- **Discriminator strings** (e.g. `type`, `status`, `action`) must be extracted to `companion object` constants or a dedicated `object` — never hardcoded inline at multiple sites.
- **Companion object constants**: `SCREAMING_SNAKE_CASE` (e.g. `private const val MAX_RETRY_COUNT`).

### Class member ordering

```
1. abstract val / abstract var
2. abstract fun
3. public val / public var (including internal)
4. private val / private var (including protected)
5. companion object { }
6. init { }
7. override fun
8. public fun (including internal)
9. protected fun
10. private fun
```

### Constructor rules

- Prefer named parameters for readability when a constructor has 3+ parameters.
- Data classes: list parameters one per line when there are 3 or more.
- Never use positional-only arguments for Boolean parameters — always use named form.

---

## 3. Testing Conventions

- Unit test files live alongside the source in the same module under `src/test/`.
- Test class names: `<ClassUnderTest>Test` (e.g. `UserRepositoryTest`).
- Test function names: describe the scenario in plain language using backtick functions — `` `given valid input, returns expected result`() ``.
- Mock external dependencies; never mock the class under test.
- Each test should assert exactly one behaviour.

---

## 4. Development Process

- Branch off `develop`; branch names follow `feature/<ticket>-short-description`.
- Commit messages follow Conventional Commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`.
- Every PR requires at least one reviewer approval before merge.
- Run unit tests locally before opening a PR.
