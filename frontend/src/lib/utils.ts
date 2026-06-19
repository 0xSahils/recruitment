import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(dateStr: string | null): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

export function formatExperience(months: number | null): string {
  if (!months) return "0 years";
  const years = Math.floor(months / 12);
  const remaining = months % 12;
  if (years === 0) return `${remaining} months`;
  if (remaining === 0) return `${years} year${years > 1 ? "s" : ""}`;
  return `${years}y ${remaining}m`;
}

export function scoreColor(score: number): string {
  if (score >= 80) return "text-green-600 bg-green-50";
  if (score >= 60) return "text-amber-600 bg-amber-50";
  return "text-gray-600 bg-gray-50";
}
