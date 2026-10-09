import { translations } from "../sdk";

import en from "./languages/en/landing.json";

// LandingPage is app-owned, so its copy doesn't belong in the upstream
// NAMESPACES list in mystic_auth/translations/translations.ts. addResourceBundle
// registers this "landing" namespace here instead. Imported once for its
// side effect (LandingPage.tsx imports this module before it renders).
translations.addResourceBundle("en", "landing", en, true, true);
