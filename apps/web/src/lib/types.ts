export type Category = "auto" | "home" | "renters" | "health" | "life" | "travel" | "pet" | "commercial";
export type Severity = "attention" | "review" | "info";
export type Certainty = "confirmed" | "possible";
export type Confidence = "high" | "moderate" | "needs_verification" | "human_review";
export type CoverageHealth = "healthy" | "review" | "attention" | "inactive";

export interface User {
  id: string;
  email: string;
  full_name: string;
  preferred_name: string | null;
  roles: string[];
  is_demo: boolean;
  onboarding_complete: boolean;
  preferences: { theme?: "light" | "dark" | "system"; reduced_motion?: boolean; low_power_3d?: boolean };
  permissions: string[];
}

export interface PolicyCard {
  id: string;
  category: Category;
  product_name: string;
  carrier: { name: string; short_name: string; color: string | null; phone: string | null; rating: string | null };
  policy_number: string;
  status: string;
  premium_annual: number;
  premium_monthly: number;
  prior_premium_annual: number | null;
  deductible: number | null;
  effective_date: string;
  expiration_date: string;
  days_until_renewal: number;
  summary: string | null;
  coverage_health: CoverageHealth;
  alerts: { title: string; severity: Severity }[];
  claim_status: string | null;
  open_claims: number;
  deductible_remaining?: number;
  oop_remaining?: number;
  deductible_progress?: number;
  oop_progress?: number;
  coverage_amount?: number | null;
  beneficiary_status?: string;
}

export interface SourceRef { section: string | null; page: number | null }

export interface PolicyDetail extends PolicyCard {
  details: Record<string, unknown>;
  coverages: { id: string; code: string; name: string; plain_language: string; limit: string | null; limit_amount: number | null; deductible: number | null; status: "covered" | "partial" | "not_covered" | "review"; source: SourceRef }[];
  exclusions: { id: string; name: string; plain_language: string; source: SourceRef }[];
  endorsements: { id: string; code: string; name: string; plain_language: string; limit_amount: number | null; premium_annual: number | null; source: SourceRef }[];
  beneficiaries: { name: string; relationship: string; designation: string; share: number }[];
  documents: DocumentItem[];
  claims: ClaimCard[];
  renewal_changes: Record<string, unknown>;
  explainer: PolicyExplainer;
}

export interface PolicyExplainer {
  title: string;
  summary: string | null;
  covered: { name: string; detail: string; limit: string; source: string | null }[];
  not_covered: { name: string; detail: string; source: string | null }[];
  deductible: string;
  limits: { name: string; limit: string }[];
  endorsements: { name: string; detail: string; limit: string; source: string }[];
  potential_gaps: { name: string; detail: string }[];
  renewal_date: string;
  premium: number;
}

export interface ClaimCard {
  id: string;
  claim_number: string;
  category: Category;
  title: string;
  status: string;
  stage: string;
  incident_date: string;
  amount_claimed: number | null;
  amount_paid: number | null;
  missing_documents: string[];
  progress: number;
  policy_id: string;
}

export interface ClaimEvent { id: string; kind: string; title: string; description: string | null; status: "done" | "current" | "upcoming" | "blocked"; occurred_at: string }

export interface ClaimDetail extends ClaimCard {
  description: string;
  deductible_applied: number | null;
  adjuster: { name: string; email: string } | null;
  denial_reason: string | null;
  deadlines: { label: string; due: string; source: string }[];
  details: Record<string, unknown>;
  events: ClaimEvent[];
  documents: DocumentItem[];
  denial_analysis?: DenialAnalysis;
  packet: ClaimPacket;
}

export interface DenialAnalysis {
  claim_number: string;
  denial_reason: string;
  explanation: string;
  findings: { kind: string; title: string; detail: string; source: string; certainty: Certainty }[];
  open_questions: string[];
  deadline: { label: string; due: string; source: string } | null;
  certainty: Certainty;
}

export interface ClaimPacket {
  claim_number: string;
  policy: string | null;
  documents_included: string[];
  documents_missing: string[];
  timeline: { title: string; date: string; status: string }[];
  ready_to_submit: boolean;
}

export interface Finding {
  id: string;
  kind: string;
  title: string;
  explanation: string;
  severity: Severity;
  certainty: Certainty;
  category: Category;
  link: string;
  source: string | null;
  amount: number | null;
  actions: string[];
}

export interface HealthScore {
  score: number;
  band: "healthy" | "good" | "needs_attention";
  headline: string;
  positives: { label: string; category: Category }[];
  factors: { label: string; severity: Severity; certainty: Certainty; category: Category; impact: number }[];
  disclaimer: string;
}

export interface Dashboard {
  greeting: string;
  name: string;
  daily_summary: { greeting_name: string; headline: string; items: string[] };
  health_score: HealthScore;
  stats: { actions_needed: number; renewals_upcoming: number; potential_savings: number; active_claims: number };
  savings: { total: number; items: { label: string; amount: number; certainty: Certainty; note: string }[] };
  layout: string[];
  actions: Finding[];
  policies: PolicyCard[];
  claims: ClaimCard[];
  authorizations: { id: string; procedure: string; status: string; decision_due: string | null; missing: string[] }[];
  empty_categories: Category[];
}

export interface DocumentItem {
  id: string;
  title: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  doc_type: string;
  status: "processing" | "ready" | "failed";
  page_count: number;
  summary: string | null;
  extracted: { monetary_amounts?: number[]; dates?: string[]; deadlines?: string[]; action_items?: string[]; policy_terms?: string[] };
  classification_confidence: string | null;
  policy_id: string | null;
  claim_id: string | null;
  created_at: string | null;
}

export interface Citation { document_id: string; document_title: string; section: string | null; page: number | null; chunk_id: string; snippet: string; label: string }

export interface AIActionItem {
  id: string;
  kind: string;
  title: string;
  what: string;
  why: string;
  data_shared: string[];
  recipient: string | null;
  status: "pending" | "approved" | "executed" | "cancelled" | "failed";
  risk_level: string;
  preview?: string | null;
  result?: Record<string, unknown>;
}

export interface AICard { type: string; data: any } // eslint-disable-line @typescript-eslint/no-explicit-any

export interface ExplainPayload {
  reasoning_summary: string;
  tools_used: string[];
  data_used: string[];
  sources: string[];
  limitations: string[];
  confidence: Confidence;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  agent?: string;
  confidence?: Confidence;
  citations?: Citation[];
  cards?: AICard[];
  actions?: AIActionItem[];
  suggestions?: string[];
  explain?: ExplainPayload;
  streaming?: boolean;
  progress?: ProgressEvent[];
  error?: string;
}

export type OrbState =
  | "idle" | "listening" | "understanding" | "retrieving" | "analyzing" | "tool"
  | "generating" | "awaiting_confirmation" | "completed" | "error" | "human_review";

export interface ProgressEvent { type: "status" | "tool" | "route"; state?: OrbState; label?: string; tool?: string; agent?: string; ok?: boolean }

export interface Notification { id: string; title: string; body: string; category: string; priority: number; link: string | null; read: boolean; created_at: string | null }

export interface SearchResult { type: string; id: string; title: string; subtitle: string | null; link: string; score: number }

export interface GraphNode { id: string; type: string; label: string; status: string; category?: Category; summary?: string; alerts?: string[]; premium?: number; carrier?: string; link?: string }
export interface GraphData { nodes: GraphNode[]; links: { source: string; target: string; kind: string }[] }
