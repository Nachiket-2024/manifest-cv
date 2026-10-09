import React from "react";
import { Navigate, Link as RouterLink } from "react-router";
import { useTranslation } from "react-i18next";
import { ArrowRight, BriefcaseBusiness, Check, ClipboardCheck, FileText, LockKeyhole, Sparkles, Target } from "lucide-react";

import { useAuthStore, APP_NAME, SUPPORT_EMAIL, AuthInlineLink, Button, Card, ControlCluster, Logo } from "../sdk";
import "../translations/registerLandingTranslations";

const HIGHLIGHTS = [
    { icon: Target, key: "knowledgeBase" },
    { icon: Sparkles, key: "aiTailoring" },
    { icon: FileText, key: "refineExport" },
    { icon: ClipboardCheck, key: "trackApplications" },
] as const;
const WORKFLOW_STEPS = ["capture", "shape", "followThrough"] as const;

const LandingPage: React.FC = () => {
    const { t } = useTranslation("landing");
    const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
    if (isAuthenticated) return <Navigate to="/dashboard" replace />;

    return (
        <div className="relative min-h-screen overflow-x-hidden bg-bg-canvas text-fg-default">
            <a href="#main-content" className="sr-only z-50 rounded-md bg-bg-surface px-3 py-2 text-sm font-semibold text-fg-default shadow-card focus:not-sr-only focus:absolute focus:left-4 focus:top-4">{t("skipToContent")}</a>
            <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(680px_420px_at_9%_0%,color-mix(in_srgb,var(--brand-solid)_23%,transparent),transparent_68%),radial-gradient(620px_420px_at_92%_9%,color-mix(in_srgb,var(--accent-solid)_16%,transparent),transparent_70%)]" />
            <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10 opacity-30 [background-image:linear-gradient(color-mix(in_srgb,var(--border-strong)_24%,transparent)_1px,transparent_1px),linear-gradient(90deg,color-mix(in_srgb,var(--border-strong)_24%,transparent)_1px,transparent_1px)] [background-size:48px_48px] [mask-image:linear-gradient(to_bottom,black,transparent_72%)]" />

            <header className="mx-auto flex w-full max-w-7xl items-center justify-between gap-4 px-5 py-5 sm:px-8 lg:px-10">
                <RouterLink to="/" aria-label={t("brandHome", { appName: APP_NAME })} className="rounded-md focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"><Logo size="sm" /></RouterLink>
                <nav aria-label={t("primaryNavigation")} className="flex items-center gap-2 sm:gap-3">
                    <ControlCluster />
                    <Button asChild variant="brand-outline" size="sm" className="border-2"><RouterLink to="/login">{t("logIn")}</RouterLink></Button>
                    <Button asChild variant="brand" size="sm"><RouterLink to="/signup">{t("signUp")}</RouterLink></Button>
                </nav>
            </header>

            <main id="main-content" tabIndex={-1} className="mx-auto max-w-7xl px-5 pb-12 outline-none sm:px-8 lg:px-10 lg:pb-20">
                <section aria-labelledby="landing-hero-title" className="grid items-center gap-12 pb-16 pt-10 lg:grid-cols-[minmax(0,1.05fr)_minmax(420px,0.95fr)] lg:gap-16 lg:pb-24 lg:pt-16">
                    <div className="max-w-2xl">
                        <h1 id="landing-hero-title" className="max-w-2xl text-5xl font-semibold leading-[1.03] tracking-[-0.045em] sm:text-6xl lg:text-7xl">{t("hero.title")}</h1>
                        <p className="mt-6 max-w-xl text-lg leading-8 text-fg-muted sm:text-xl">{t("hero.subtitle", { appName: APP_NAME })}</p>
                        <div className="mt-8 flex flex-wrap items-center gap-3">
                            <Button asChild variant="brand" size="lg" className="group"><RouterLink to="/signup">{t("hero.getStarted")}<ArrowRight className="transition-transform duration-150 group-hover:translate-x-0.5" aria-hidden="true" /></RouterLink></Button>
                            <Button asChild variant="brand-outline" size="lg" className="border-2"><RouterLink to="/login">{t("logIn")}</RouterLink></Button>
                        </div>
                        <div className="mt-7 flex flex-wrap gap-x-5 gap-y-2 text-sm text-fg-muted">
                            <span className="inline-flex items-center gap-2"><LockKeyhole size={15} className="text-brand-fg" aria-hidden="true" />{t("hero.trust.private")}</span>
                            <span className="inline-flex items-center gap-2"><Check size={15} className="text-brand-fg" aria-hidden="true" />{t("hero.trust.control")}</span>
                        </div>
                    </div>

                    <div className="relative mx-auto w-full max-w-xl lg:mx-0 lg:justify-self-end">
                        <div aria-hidden="true" className="absolute -inset-4 rounded-[2rem] bg-brand-solid/10 blur-2xl" />
                        <Card className="relative overflow-hidden border-brand-border/80 bg-bg-surface/95 p-0 shadow-[0_26px_70px_-32px_var(--brand-solid)]">
                            <div className="flex items-center justify-between border-b border-border-card bg-bg-card-head/70 px-5 py-4">
                                <div className="flex items-center gap-3"><div className="grid size-9 place-items-center rounded-lg bg-brand-solid text-brand-contrast"><BriefcaseBusiness size={18} aria-hidden="true" /></div><div><p className="text-sm font-semibold">{t("preview.workspace")}</p><p className="text-xs text-fg-muted">{t("preview.workspaceStatus")}</p></div></div>
                                <span className="rounded-full border border-brand-border bg-brand-tile-subtle px-2.5 py-1 text-xs font-semibold text-brand-fg">{t("preview.ready")}</span>
                            </div>
                            <div className="space-y-5 p-5 sm:p-7">
                                <div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand-fg">{t("preview.matchLabel")}</p><h2 className="mt-2 text-2xl font-semibold tracking-tight">{t("preview.role")}</h2><p className="mt-1 text-sm text-fg-muted">{t("preview.company")}</p></div>
                                <div className="rounded-xl border border-border-card bg-bg-canvas/70 p-4"><div className="mb-4 flex items-center justify-between text-xs text-fg-muted"><span>{t("preview.matchingExperience")}</span><span className="font-semibold text-brand-fg">92%</span></div><div className="h-2 overflow-hidden rounded-full bg-bg-muted"><div className="h-full w-[92%] rounded-full bg-brand-solid" /></div><div className="mt-5 space-y-3">{["discovery", "systems", "leadership"].map((item) => <div key={item} className="flex items-center gap-3 text-sm"><span className="grid size-5 place-items-center rounded-full bg-brand-tile-subtle text-brand-fg"><Check size={12} aria-hidden="true" /></span><span>{t(`preview.skills.${item}`)}</span></div>)}</div></div>
                                <div className="grid grid-cols-3 gap-2 text-center">{(["source", "draft", "sent"] as const).map((item, index) => <div key={item} className={`rounded-lg border px-2 py-3 ${index === 1 ? "border-brand-border bg-brand-tile-subtle" : "border-border-card bg-bg-canvas/50"}`}><p className="text-xs text-fg-default">{t(`preview.pipeline.${item}`)}</p><p className={`mt-1 text-sm font-semibold ${index === 1 ? "text-brand-fg" : "text-fg-default"}`}>{index === 1 ? t("preview.pipeline.active") : t("preview.pipeline.done")}</p></div>)}</div>
                            </div>
                        </Card>
                    </div>
                </section>

                <section aria-labelledby="landing-highlights-title" className="border-t border-border-card pt-12 lg:pt-16">
                    <div className="mb-7 flex flex-col justify-between gap-3 sm:flex-row sm:items-end"><div><p className="text-sm font-semibold text-brand-fg">{t("highlights.eyebrow")}</p><h2 id="landing-highlights-title" className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">{t("highlights.heading")}</h2></div><p className="max-w-md text-sm leading-6 text-fg-muted">{t("highlights.description")}</p></div>
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">{HIGHLIGHTS.map(({ icon: HighlightIcon, key }, index) => <Card as="article" key={key} className="group p-5 hover:-translate-y-0.5"><div className="mb-8 flex items-center justify-between"><div className="grid size-10 place-items-center rounded-xl border border-brand-border bg-brand-tile-subtle text-brand-fg"><HighlightIcon size={19} aria-hidden="true" /></div><span className="text-xs font-semibold text-fg-muted">0{index + 1}</span></div><h3 className="font-semibold">{t(`highlights.${key}.title`)}</h3><p className="mt-2 text-sm leading-6 text-fg-muted">{t(`highlights.${key}.description`)}</p></Card>)}</div>
                </section>

                <section aria-labelledby="landing-workflow-title" className="mt-16 grid gap-8 rounded-2xl border border-border-card bg-bg-surface/70 p-6 sm:p-8 lg:grid-cols-[0.8fr_1.2fr] lg:items-center lg:p-10"><div><p className="text-sm font-semibold text-brand-fg">{t("workflow.eyebrow")}</p><h2 id="landing-workflow-title" className="mt-2 text-3xl font-semibold tracking-tight">{t("workflow.heading")}</h2><p className="mt-3 max-w-md text-sm leading-6 text-fg-muted">{t("workflow.description")}</p></div><div className="grid gap-3 sm:grid-cols-3">{WORKFLOW_STEPS.map((step, index) => <div key={step} className="rounded-xl border border-border-card bg-bg-canvas/60 p-4"><span className="text-xs font-semibold text-brand-fg">0{index + 1}</span><h3 className="mt-8 font-semibold">{t(`workflow.${step}.title`)}</h3><p className="mt-2 text-sm leading-5 text-fg-muted">{t(`workflow.${step}.description`)}</p></div>)}</div></section>
            </main>

            <footer className="mx-auto flex max-w-7xl justify-between gap-4 px-5 py-6 text-sm text-fg-muted sm:px-8 lg:px-10"><span>{t("footer.tagline", { appName: APP_NAME })}</span><nav aria-label={t("footerNavigation")} className="flex flex-wrap justify-end gap-x-4 gap-y-2"><AuthInlineLink to="/privacy">{t("footer.privacyPolicy")}</AuthInlineLink><AuthInlineLink to="/terms">{t("footer.termsOfService")}</AuthInlineLink>{SUPPORT_EMAIL && <a className="font-semibold text-brand-fg hover:underline" href={`mailto:${SUPPORT_EMAIL}`}>{t("footer.support")}</a>}</nav></footer>
        </div>
    );
};

export default LandingPage;
