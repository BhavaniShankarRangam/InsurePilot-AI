import {
  ArrowRight,
  Bot,
  Camera,
  CircleCheck,
  Eye,
  FileSearch,
  GitCompare,
  HeartPulse,
  Hand,
  KeyRound,
  Lock,
  Mic,
  Play,
  Receipt,
  ScanLine,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  Upload,
  Wallet,
  Workflow,
} from "lucide-react";
import Link from "next/link";
import { Logo } from "@/components/brand/logo";
import { DemoChat } from "@/components/landing/demo-chat";
import { HeroVisual, UniversePreview } from "@/components/landing/visuals";

const AGENTS = [
  ["Policy Intelligence", "Translates any policy into plain English."],
  ["Claims", "Guides you from first report to payment."],
  ["Coverage", "Answers “am I covered?” — with sources."],
  ["Renewal", "Explains premium changes before you renew."],
  ["Medical Insurance", "Navigates costs, EOBs and authorizations."],
  ["Provider Network", "Finds in-network care."],
  ["Risk", "Spots gaps, expirations and discrepancies."],
  ["Shopping", "Compares equivalent coverage objectively."],
  ["Document Intelligence", "Reads, classifies and extracts deadlines."],
  ["Communication", "Drafts emails and appeals you can edit."],
  ["Fraud Signal", "Flags scams pretending to be your insurer."],
  ["Human Escalation", "Hands off to a licensed professional."],
];

export default function LandingPage() {
  return (
    <div className="relative overflow-x-clip">
      <div className="ambient" aria-hidden />
      <header className="fixed inset-x-0 top-0 z-50">
        <nav className="glass mx-auto mt-3 flex h-14 max-w-6xl items-center justify-between rounded-2xl px-4 md:mx-6 lg:mx-auto" aria-label="Main">
          <Link href="/" aria-label="InsurePilot home"><Logo /></Link>
          <div className="hidden items-center gap-6 text-sm text-muted md:flex">
            <a href="#how" className="hover:text-fg">How it works</a>
            <a href="#agents" className="hover:text-fg">AI agents</a>
            <a href="#claims" className="hover:text-fg">Claims</a>
            <a href="#health" className="hover:text-fg">Health</a>
            <a href="#privacy" className="hover:text-fg">Privacy</a>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/login" className="hidden rounded-xl px-3 py-2 text-sm text-muted hover:text-fg sm:block">Sign in</Link>
            <Link href="/login" className="bg-accent-gradient rounded-xl px-4 py-2 text-sm font-medium text-white shadow-glow">Try InsurePilot</Link>
          </div>
        </nav>
      </header>

      <main id="main">
        {/* HERO */}
        <section className="relative mx-auto grid min-h-[100dvh] max-w-7xl items-center gap-8 px-6 pt-28 lg:grid-cols-2">
          <div className="grid-bg pointer-events-none absolute inset-0" aria-hidden />
          <div className="relative z-10">
            <p className="glass mb-6 inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs text-muted">
              <Sparkles className="size-3.5 text-accent" aria-hidden /> One AI for all your insurance
            </p>
            <h1 className="font-display text-5xl font-semibold leading-[1.02] tracking-tight md:text-7xl">
              Your insurance <span className="text-gradient">finally works</span> for you.
            </h1>
            <p className="mt-6 max-w-xl text-lg text-muted md:text-xl">
              InsurePilot connects your policies, claims, benefits and documents into one intelligent AI assistant.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/login" className="bg-accent-gradient inline-flex h-12 items-center gap-2 rounded-2xl px-6 font-medium text-white shadow-glow transition hover:brightness-110">
                Try InsurePilot <ArrowRight className="size-4" aria-hidden />
              </Link>
              <a href="#demo" className="glass inline-flex h-12 items-center gap-2 rounded-2xl px-6 font-medium transition hover:bg-surface-hover">
                <Play className="size-4" aria-hidden /> Watch Demo
              </a>
            </div>
            <ul className="mt-10 flex flex-wrap gap-x-6 gap-y-2 text-sm text-muted">
              {["Every answer cites its source", "Never acts without approval", "Plain English, always"].map((t) => (
                <li key={t} className="flex items-center gap-1.5"><CircleCheck className="size-4 text-ok" aria-hidden /> {t}</li>
              ))}
            </ul>
          </div>
          <div className="relative h-[420px] md:h-[560px]">
            <HeroVisual />
          </div>
        </section>

        {/* DEMO */}
        <section id="demo" className="mx-auto max-w-6xl scroll-mt-24 px-6 py-24">
          <div className="grid items-center gap-12 lg:grid-cols-2">
            <div>
              <p className="text-sm font-medium uppercase tracking-[0.18em] text-accent">Interactive AI</p>
              <h2 className="mt-3 font-display text-4xl font-semibold tracking-tight">Just ask. It checks your actual policy.</h2>
              <p className="mt-4 text-lg text-muted">Every policy-specific answer comes from your structured policy data, a retrieved document passage, or a verified tool result — with the page number. If it can’t verify something, it says so.</p>
              <div className="mt-6 grid grid-cols-2 gap-3 text-sm">
                {[[Mic, "Talk or type"], [FileSearch, "Cites sources"], [Eye, "Why am I seeing this?"], [Hand, "You approve every action"]].map(([I, t]) => {
                  const Icon = I as typeof Mic;
                  return <div key={t as string} className="glass flex items-center gap-2 rounded-xl px-3 py-2.5"><Icon className="size-4 text-accent" aria-hidden /> {t as string}</div>;
                })}
              </div>
            </div>
            <DemoChat />
          </div>
        </section>

        {/* UNIVERSE */}
        <section className="mx-auto max-w-6xl px-6 py-16">
          <div className="mb-8 text-center">
            <p className="text-sm font-medium uppercase tracking-[0.18em] text-accent">Insurance Universe</p>
            <h2 className="mt-3 font-display text-4xl font-semibold tracking-tight">See everything you protect — connected.</h2>
            <p className="mx-auto mt-3 max-w-2xl text-muted">Your Insurance Digital Twin links you, your car, home, health and family to every policy, carrier, claim and provider. Hover to explore.</p>
          </div>
          <div className="relative h-[520px] overflow-hidden rounded-[28px] bg-[#07080d] shadow-lift ring-1 ring-border">
            <UniversePreview />
          </div>
        </section>

        {/* HOW IT WORKS */}
        <section id="how" className="mx-auto max-w-6xl scroll-mt-24 px-6 py-24">
          <h2 className="text-center font-display text-4xl font-semibold tracking-tight">Set up in under five minutes</h2>
          <ol className="mt-12 grid gap-4 md:grid-cols-3">
            {[
              [Upload, "Connect or upload", "Link a carrier or drop in a policy PDF, EOB, bill or photo."],
              [ScanLine, "AI organizes everything", "OCR, extraction and your Digital Twin — automatically. You confirm the details."],
              [Sparkles, "Ask anything", "“Handle my insurance.” InsurePilot watches renewals, gaps, claims and bills for you."],
            ].map(([I, t, d], i) => {
              const Icon = I as typeof Upload;
              return (
                <li key={t as string} className="glass rounded-3xl p-7">
                  <span className="text-sm font-semibold text-accent">0{i + 1}</span>
                  <Icon className="mt-4 size-7 text-accent" aria-hidden />
                  <h3 className="mt-4 font-display text-xl font-semibold">{t as string}</h3>
                  <p className="mt-2 text-muted">{d as string}</p>
                </li>
              );
            })}
          </ol>
        </section>

        {/* AGENTS */}
        <section id="agents" className="mx-auto max-w-6xl scroll-mt-24 px-6 py-16">
          <div className="text-center">
            <p className="text-sm font-medium uppercase tracking-[0.18em] text-accent">Multi-agent AI</p>
            <h2 className="mt-3 font-display text-4xl font-semibold tracking-tight">A supervisor and twelve specialists</h2>
            <p className="mx-auto mt-3 max-w-2xl text-muted">A LangGraph supervisor routes each request to the right expert. Each has its own tools, permissions, confidence scoring and escalation rules.</p>
          </div>
          <ul className="mt-10 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {AGENTS.map(([n, d]) => (
              <li key={n} className="glass rounded-2xl p-5 transition hover:-translate-y-1 hover:shadow-lift">
                <Bot className="size-5 text-accent" aria-hidden />
                <p className="mt-3 font-medium">{n} Agent</p>
                <p className="mt-1 text-sm text-muted">{d}</p>
              </li>
            ))}
          </ul>
        </section>

        {/* FEATURES */}
        <section className="mx-auto grid max-w-6xl gap-4 px-6 py-24 lg:grid-cols-2">
          {[
            { id: "wallet", icon: Wallet, title: "Insurance Wallet", body: "Every policy on one screen: carrier, premium, renewal, coverage health and claim status — swipeable on mobile." },
            { id: "claims", icon: Workflow, title: "Claim Guardian", body: "Guided accident reports, missing-document detection, deadline monitoring, photo AI, and denial analysis that checks your endorsements." },
            { id: "health", icon: HeartPulse, title: "Medical Insurance AI", body: "“Can I get an MRI here?” Network, procedure code, deductible, coinsurance and prior-auth checks — plus bill vs. EOB reconciliation." },
            { id: "compare", icon: GitCompare, title: "Policy comparison", body: "Normalized side-by-side coverage. Objective differences, never a “best” label." },
          ].map((f) => (
            <article key={f.id} id={f.id} className="glass scroll-mt-24 rounded-3xl p-8">
              <f.icon className="size-7 text-accent" aria-hidden />
              <h3 className="mt-4 font-display text-2xl font-semibold">{f.title}</h3>
              <p className="mt-2 text-muted">{f.body}</p>
            </article>
          ))}
          <article className="glass rounded-3xl p-8 lg:col-span-2">
            <div className="grid gap-6 md:grid-cols-3">
              {[[Camera, "Camera-first", "Scan cards, bills and accident scenes."], [Receipt, "Bill reconciliation", "Catch billing discrepancies before you pay."], [Stethoscope, "Prior authorization", "Find missing paperwork before a denial."]].map(([I, t, d]) => {
                const Icon = I as typeof Camera;
                return <div key={t as string}><Icon className="size-6 text-accent" aria-hidden /><p className="mt-3 font-medium">{t as string}</p><p className="text-sm text-muted">{d as string}</p></div>;
              })}
            </div>
          </article>
        </section>

        {/* PRIVACY & SECURITY */}
        <section id="privacy" className="mx-auto max-w-6xl scroll-mt-24 px-6 py-16">
          <div className="glass-strong grid gap-10 rounded-[32px] p-10 lg:grid-cols-2">
            <div>
              <Lock className="size-8 text-accent" aria-hidden />
              <h2 className="mt-4 font-display text-4xl font-semibold tracking-tight">Private by design. You stay in control.</h2>
              <p className="mt-3 text-muted">A Privacy Center shows what data exists, why it’s used, what’s shared and every AI action — with export and delete in one click.</p>
            </div>
            <ul className="grid gap-3 sm:grid-cols-2">
              {[[KeyRound, "Encrypted at rest & in transit"], [ShieldCheck, "Role-based access & audit logs"], [Hand, "Approval for every sensitive action"], [Eye, "Explainable AI on every answer"], [Lock, "PII masking & consent management"], [FileSearch, "Never invents coverage"]].map(([I, t]) => {
                const Icon = I as typeof Lock;
                return <li key={t as string} className="flex items-center gap-2.5 rounded-2xl bg-surface px-4 py-3 text-sm"><Icon className="size-4 shrink-0 text-accent" aria-hidden /> {t as string}</li>;
              })}
            </ul>
          </div>
        </section>

        {/* CTA */}
        <section className="mx-auto max-w-4xl px-6 py-28 text-center">
          <h2 className="font-display text-5xl font-semibold tracking-tight">Insurance, finally <span className="text-gradient">understandable.</span></h2>
          <p className="mt-4 text-lg text-muted">Explore the full product with a realistic demo profile — no sign-up needed.</p>
          <Link href="/login" className="bg-accent-gradient mt-8 inline-flex h-14 items-center gap-2 rounded-2xl px-8 text-lg font-medium text-white shadow-glow transition hover:brightness-110">
            Try InsurePilot <ArrowRight className="size-5" aria-hidden />
          </Link>
        </section>
      </main>
      <footer className="border-t border-border px-6 py-10">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 text-sm text-muted md:flex-row">
          <Logo />
          <p>InsurePilot explains coverage; your insurer makes coverage decisions. Not financial, legal or medical advice.</p>
        </div>
      </footer>
    </div>
  );
}
