/**
 * Registers ManifestCV's own translation namespaces onto mystic-auth's
 * shared i18next instance re-exported from the upstream SDK. Uses i18next's own `addResourceBundle` API - a normal
 * library call, not an edit to any mystic_auth file - so this is entirely
 * additive on top of the setup docs/mystic_auth/translations/overview.md
 * describes.
 *
 * One namespace per feature folder, mirroring mystic_auth/translations/
 * translations.ts's own convention, plus one "app_common" namespace for
 * vocabulary shared across ManifestCV's own pages (pager, nav labels,
 * application status words) - same rationale as mystic_auth's own
 * "ui_text" namespace.
 *
 * Imported once, eagerly, from main.tsx - see that file's comment on why
 * this must run after mystic_auth/store/languageStore.ts (which is what
 * actually calls i18next's `init()`; addResourceBundle requires an
 * already-initialized instance).
 */
// Keep the translation bootstrap narrow. Importing the app SDK here would
// eagerly evaluate every SDK re-export, including router and error-boundary
// modules, before isolated Mystic Auth unit tests can install their mocks.
// The shared translation registry is the only foundation capability needed
// by this initializer, so consume that capability directly.
import translations from "../../mystic_auth/translations/translations";

import enAppCommon from "./languages/en/app_common.json";
import enCareerKnowledge from "./languages/en/career_knowledge.json";
import enApplications from "./languages/en/applications.json";
import enErrors from "./languages/en/errors.json";

import hiAppCommon from "./languages/hi/app_common.json";
import hiCareerKnowledge from "./languages/hi/career_knowledge.json";
import hiApplications from "./languages/hi/applications.json";
import hiErrors from "./languages/hi/errors.json";

import mrAppCommon from "./languages/mr/app_common.json";
import mrCareerKnowledge from "./languages/mr/career_knowledge.json";
import mrApplications from "./languages/mr/applications.json";
import mrErrors from "./languages/mr/errors.json";

import guAppCommon from "./languages/gu/app_common.json";
import guCareerKnowledge from "./languages/gu/career_knowledge.json";
import guApplications from "./languages/gu/applications.json";
import guErrors from "./languages/gu/errors.json";

// The upstream translation initializer keeps its imported JSON objects as the
// i18next resource roots. Keep references here so the additive app merge can
// detach from those roots below; this avoids changing the object that the
// upstream parity test imports directly.
import enMysticErrors from "../../mystic_auth/translations/languages/en/errors.json";
import hiMysticErrors from "../../mystic_auth/translations/languages/hi/errors.json";
import mrMysticErrors from "../../mystic_auth/translations/languages/mr/errors.json";
import guMysticErrors from "../../mystic_auth/translations/languages/gu/errors.json";

export const APP_NAMESPACES = ["app_common", "career_knowledge", "applications"] as const;
export type AppNamespace = (typeof APP_NAMESPACES)[number];

const APP_RESOURCES: Record<string, Record<AppNamespace, object>> = {
    en: {
        app_common: enAppCommon,
        career_knowledge: enCareerKnowledge,
        applications: enApplications,
    },
    hi: {
        app_common: hiAppCommon,
        career_knowledge: hiCareerKnowledge,
        applications: hiApplications,
    },
    mr: {
        app_common: mrAppCommon,
        career_knowledge: mrCareerKnowledge,
        applications: mrApplications,
    },
    gu: {
        app_common: guAppCommon,
        career_knowledge: guCareerKnowledge,
        applications: guApplications,
    },
};

for (const [language, namespaces] of Object.entries(APP_RESOURCES)) {
    for (const [namespace, resource] of Object.entries(namespaces)) {
        translations.addResourceBundle(language, namespace, resource, true, true);
    }
}

// AppError codes ManifestCV's own routes raise (see backend/app/api/*)
// merged straight into mystic_auth's existing "errors" namespace, not a
// namespace of our own - apiError.ts's extractApiErrorMessage() always
// looks up `errors:${code}` in that one fixed namespace. `deep: true` so
// this merges keys in rather than replacing mystic_auth's own entries.
const APP_ERRORS: Record<string, object> = {
    en: enErrors,
    hi: hiErrors,
    mr: mrErrors,
    gu: guErrors,
};

for (const [language, resource] of Object.entries(APP_ERRORS)) {
    // i18next mutates the existing resource root while deep-merging. Detach
    // the merged bundle from mystic-auth's imported JSON object so the
    // upstream parity test still sees the upstream JSON shape directly.
    const upstreamErrors = { en: enMysticErrors, hi: hiMysticErrors, mr: mrMysticErrors, gu: guMysticErrors }[language];
    const merged = { ...translations.getResourceBundle(language, "errors"), ...resource };
    for (const key of Object.keys(resource)) delete (upstreamErrors as Record<string, unknown>)[key];
    translations.removeResourceBundle(language, "errors");
    translations.addResourceBundle(language, "errors", merged, true, true);
}
