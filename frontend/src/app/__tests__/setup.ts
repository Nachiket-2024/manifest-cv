// Registers ManifestCV's own translation namespaces (career_knowledge,
// resumes, applications, app_common) before any test renders a component,
// same rationale as mystic_auth's own __tests__/setup.ts importing its
// translations module: without this, useTranslation() has no resources
// loaded for these namespaces and falls back to rendering raw keys (e.g.
// "pager.next") instead of the actual English text tests assert against.
// Listed after mystic_auth's own setup file in vitest.config.ts's
// setupFiles, since this relies on i18next already being init()'d there
// (addResourceBundle requires an already-initialized instance).
import "../translations/translations";
