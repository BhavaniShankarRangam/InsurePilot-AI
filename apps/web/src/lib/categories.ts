import {
  Briefcase,
  Building2,
  Car,
  HeartPulse,
  House,
  PawPrint,
  Plane,
  Umbrella,
  type LucideIcon,
} from "lucide-react";
import type { Category } from "./types";

export const CATEGORY_META: Record<Category, { label: string; noun: string; icon: LucideIcon; hue: string }> = {
  auto: { label: "Auto", noun: "Car", icon: Car, hue: "#5b8cff" },
  home: { label: "Home", noun: "Home", icon: House, hue: "#22b8cf" },
  renters: { label: "Renters", noun: "Apartment", icon: Building2, hue: "#4dabf7" },
  health: { label: "Health", noun: "Health", icon: HeartPulse, hue: "#2ec4a6" },
  life: { label: "Life", noun: "Life", icon: Umbrella, hue: "#8b7bff" },
  travel: { label: "Travel", noun: "Travel", icon: Plane, hue: "#b07cff" },
  pet: { label: "Pet", noun: "Pet", icon: PawPrint, hue: "#f2a33a" },
  commercial: { label: "Business", noun: "Business", icon: Briefcase, hue: "#7a8296" },
};

export const ALL_CATEGORIES = Object.keys(CATEGORY_META) as Category[];
