"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";
import type {
  AIActionItem,
  ClaimCard,
  ClaimDetail,
  Dashboard,
  DocumentItem,
  Finding,
  GraphData,
  Notification,
  PolicyCard,
  PolicyDetail,
  SearchResult,
  User,
} from "./types";

export const keys = {
  me: ["me"] as const,
  dashboard: ["dashboard"] as const,
  policies: ["policies"] as const,
  policy: (id: string) => ["policy", id] as const,
  claims: ["claims"] as const,
  claim: (id: string) => ["claim", id] as const,
  documents: ["documents"] as const,
  notifications: ["notifications"] as const,
  actions: ["ai-actions"] as const,
  activity: ["ai-activity"] as const,
};

export const useMe = () => useQuery({ queryKey: keys.me, queryFn: () => api.get<User>("/auth/me"), staleTime: 60_000 });
export const useDashboard = () => useQuery({ queryKey: keys.dashboard, queryFn: () => api.get<Dashboard>("/dashboard") });
export const usePolicies = () => useQuery({ queryKey: keys.policies, queryFn: () => api.get<PolicyCard[]>("/policies") });
export const usePolicy = (id: string) =>
  useQuery({ queryKey: keys.policy(id), queryFn: () => api.get<PolicyDetail>(`/policies/${id}`), enabled: !!id });
export const useClaims = () => useQuery({ queryKey: keys.claims, queryFn: () => api.get<ClaimCard[]>("/claims") });
export const useClaim = (id: string) =>
  useQuery({ queryKey: keys.claim(id), queryFn: () => api.get<ClaimDetail>(`/claims/${id}`), enabled: !!id });
export const useDocuments = () =>
  useQuery({
    queryKey: keys.documents,
    queryFn: () => api.get<DocumentItem[]>("/documents"),
    refetchInterval: (q) => (q.state.data?.some((d) => d.status === "processing") ? 1500 : false),
  });
export const useNotifications = () =>
  useQuery({ queryKey: keys.notifications, queryFn: () => api.get<Notification[]>("/notifications"), refetchInterval: 60_000 });
export const useActionCenter = () => useQuery({ queryKey: ["action-center"], queryFn: () => api.get<Finding[]>("/insights/actions") });
export const useGraph = () => useQuery({ queryKey: ["graph"], queryFn: () => api.get<GraphData>("/graph") });
export const usePendingActions = () =>
  useQuery({ queryKey: keys.actions, queryFn: () => api.get<AIActionItem[]>("/ai/actions?status=pending"), refetchInterval: 30_000 });
export const useSearch = (q: string) =>
  useQuery({ queryKey: ["search", q], queryFn: () => api.get<SearchResult[]>(`/search?q=${encodeURIComponent(q)}`), enabled: q.trim().length > 1, staleTime: 30_000 });

export function useFindingDecision() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, decision, days }: { id: string; decision: "ignore" | "remind"; days?: number }) =>
      api.post(`/insights/actions/${id}`, { decision, days: days ?? 3 }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.dashboard });
      qc.invalidateQueries({ queryKey: ["action-center"] });
    },
  });
}

export function useActionDecision() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, decision }: { id: string; decision: "approve" | "cancel" }) =>
      api.post<AIActionItem>(`/ai/actions/${id}/${decision}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.actions });
      qc.invalidateQueries({ queryKey: keys.activity });
      qc.invalidateQueries({ queryKey: keys.claims });
      qc.invalidateQueries({ queryKey: keys.dashboard });
    },
  });
}
