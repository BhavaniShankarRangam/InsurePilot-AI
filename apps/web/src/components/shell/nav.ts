import {
  Activity,
  ChartColumn,
  FileText,
  GitCompare,
  HeartPulse,
  LayoutDashboard,
  Lock,
  Orbit,
  Settings,
  ShieldCheck,
  Sparkles,
  Wallet,
  Workflow,
  FlaskConical,
  type LucideIcon,
} from "lucide-react";

export interface NavItem { href: string; label: string; icon: LucideIcon; mobile?: boolean; permission?: string }

export const NAV_PRIMARY: NavItem[] = [
  { href: "/dashboard", label: "Home", icon: LayoutDashboard, mobile: true },
  { href: "/assistant", label: "AI Assistant", icon: Sparkles, mobile: true },
  { href: "/wallet", label: "Insurance Wallet", icon: Wallet, mobile: true },
  { href: "/policies", label: "Policies", icon: ShieldCheck },
  { href: "/claims", label: "Claims", icon: Workflow, mobile: true },
  { href: "/health", label: "Health", icon: HeartPulse },
  { href: "/documents", label: "Documents", icon: FileText },
  { href: "/compare", label: "Compare", icon: GitCompare },
  { href: "/insights", label: "Insights", icon: ChartColumn },
  { href: "/universe", label: "Insurance Universe", icon: Orbit },
];

export const NAV_SECONDARY: NavItem[] = [
  { href: "/activity", label: "AI Activity", icon: Activity },
  { href: "/privacy", label: "Privacy Center", icon: Lock },
  { href: "/evaluations", label: "AI Evaluations", icon: FlaskConical, permission: "eval:read" },
  { href: "/settings", label: "Settings", icon: Settings },
];
