/**
 * Registers ManifestCV's own translation namespaces onto mystic-auth's
 * shared i18next instance (re-exported as `translations` from `../app_sdk`,
 * see that file's own comment on why it goes through there rather than a
 * direct import). Uses i18next's own `addResourceBundle` API — a normal
 * library call, not an edit to any mystic_auth file — so this is entirely
 * additive on top of the setup docs/mystic_auth/translations/overview.md
 * describes.
 *
 * One namespace per feature folder, mirroring mystic_auth/translations/
 * translations.ts's own convention, plus one "app_common" namespace for
 * vocabulary shared across ManifestCV's own pages (pager, nav labels,
 * application status words) — same rationale as mystic_auth's own
 * "ui_text" namespace.
 *
 * Imported once, eagerly, from main.tsx — see that file's comment on why
 * this must run after mystic_auth/store/languageStore.ts (which is what
 * actually calls i18next's `init()`; addResourceBundle requires an
 * already-initialized instance).
 */
import { translations } from "../app_sdk";

import enAppCommon from "./languages/en/app_common.json";
import enCareerKnowledge from "./languages/en/career_knowledge.json";
import enResumes from "./languages/en/resumes.json";
import enApplications from "./languages/en/applications.json";
import enErrors from "./languages/en/errors.json";

import hiAppCommon from "./languages/hi/app_common.json";
import hiCareerKnowledge from "./languages/hi/career_knowledge.json";
import hiResumes from "./languages/hi/resumes.json";
import hiApplications from "./languages/hi/applications.json";
import hiErrors from "./languages/hi/errors.json";

import mrAppCommon from "./languages/mr/app_common.json";
import mrCareerKnowledge from "./languages/mr/career_knowledge.json";
import mrResumes from "./languages/mr/resumes.json";
import mrApplications from "./languages/mr/applications.json";
import mrErrors from "./languages/mr/errors.json";

import guAppCommon from "./languages/gu/app_common.json";
import guCareerKnowledge from "./languages/gu/career_knowledge.json";
import guResumes from "./languages/gu/resumes.json";
import guApplications from "./languages/gu/applications.json";
import guErrors from "./languages/gu/errors.json";

export const APP_NAMESPACES = ["app_common", "career_knowledge", "resumes", "applications"] as const;
export type AppNamespace = (typeof APP_NAMESPACES)[number];

const APP_RESOURCES: Record<string, Record<AppNamespace, object>> = {
    en: {
        app_common: enAppCommon,
        career_knowledge: enCareerKnowledge,
        resumes: enResumes,
        applications: enApplications,
    },
    hi: {
        app_common: hiAppCommon,
        career_knowledge: hiCareerKnowledge,
        resumes: hiResumes,
        applications: hiApplications,
    },
    mr: {
        app_common: mrAppCommon,
        career_knowledge: mrCareerKnowledge,
        resumes: mrResumes,
        applications: mrApplications,
    },
    gu: {
        app_common: guAppCommon,
        career_knowledge: guCareerKnowledge,
        resumes: guResumes,
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
// namespace of our own — apiError.ts's extractApiErrorMessage() always
// looks up `errors:${code}` in that one fixed namespace. `deep: true` so
// this merges keys in rather than replacing mystic_auth's own entries.
const APP_ERRORS: Record<string, object> = {
    en: enErrors,
    hi: hiErrors,
    mr: mrErrors,
    gu: guErrors,
};

for (const [language, resource] of Object.entries(APP_ERRORS)) {
    translations.addResourceBundle(language, "errors", resource, true, true);
}
