"use client";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Navbar from "@/components/Navbar";
import { searchCandidates, exportCandidates, updateCandidate } from "@/lib/api";
import { cn, scoreColor, formatExperience } from "@/lib/utils";
import { toast } from "sonner";
import Link from "next/link";

const STATUS_OPTIONS = ["new", "contacted", "shortlisted", "interview_scheduled", "rejected", "hired"];
const STATUS_LABELS: Record<string, string> = {
  new: "New", contacted: "Contacted", shortlisted: "Shortlisted",
  interview_scheduled: "Interview", rejected: "Rejected", hired: "Hired",
};
const FILTER_TABS = ["all", ...STATUS_OPTIONS];

export default function DashboardPage() {
  const queryClient = useQueryClient();
  const [query, setQuery] = useState("");
  const [searchTrigger, setSearchTrigger] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ["search", searchTrigger],
    queryFn: () => searchCandidates(searchTrigger, { exclude_rejected: statusFilter !== "rejected" }),
    enabled: !!searchTrigger,
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) setSearchTrigger(query.trim());
  };

  const filteredResults = data?.results?.filter((r: any) =>
    statusFilter === "all" ? true : r.candidate_status === statusFilter
  ) || [];

  const handleStatusChange = async (candidateId: string, newStatus: string) => {
    try {
      await updateCandidate(candidateId, { candidate_status: newStatus });
      queryClient.invalidateQueries({ queryKey: ["search", searchTrigger] });
      toast.success("Status updated");
    } catch {
      toast.error("Failed to update status");
    }
  };

  const handleExport = async () => {
    const ids = filteredResults.map((r: any) => r.candidate_id);
    if (!ids.length) return toast.error("No candidates to export");
    try {
      await exportCandidates({ candidate_ids: ids });
      toast.success("CSV exported");
    } catch {
      toast.error("Export failed");
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900 mb-1">Find Best Candidates</h1>
          <p className="text-gray-500">Paste a Job Description or search naturally</p>
        </div>

        <form onSubmit={handleSearch} className="mb-6">
          <div className="card p-4">
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full border-0 focus:ring-0 resize-none text-gray-900 placeholder-gray-400 text-lg"
              rows={3}
              placeholder='Paste JD or type: "React developers in Bangalore with AWS and 5+ years"'
            />
            <div className="flex justify-end mt-2">
              <button type="submit" disabled={!query.trim() || isLoading} className="btn-primary">
                {isFetching ? "Searching..." : "Find Best Candidates"}
              </button>
            </div>
          </div>
        </form>

        {data && (
          <>
            {data.parsed_query && (
              <div className="card p-4 mb-4">
                <p className="text-sm text-gray-500">
                  <span className="font-medium">Parsed:</span>{" "}
                  {data.parsed_query.role && <span className="mr-3">Role: {data.parsed_query.role}</span>}
                  {data.parsed_query.required_skills?.length > 0 && (
                    <span className="mr-3">Skills: {data.parsed_query.required_skills.join(", ")}</span>
                  )}
                  {data.parsed_query.location && <span className="mr-3">Location: {data.parsed_query.location}</span>}
                  {data.parsed_query.experience?.min_years && (
                    <span>Exp: {data.parsed_query.experience.min_years}+ years</span>
                  )}
                </p>
              </div>
            )}

            <div className="flex items-center justify-between mb-4">
              <div className="flex gap-1 flex-wrap">
                {FILTER_TABS.map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setStatusFilter(tab)}
                    className={cn(
                      "px-3 py-1.5 rounded-full text-sm font-medium transition-colors",
                      statusFilter === tab ? "bg-primary-600 text-white" : "bg-white text-gray-600 border hover:bg-gray-50"
                    )}
                  >
                    {tab === "all" ? "All" : STATUS_LABELS[tab]}
                  </button>
                ))}
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm text-gray-500">{filteredResults.length} candidates</span>
                <button onClick={handleExport} className="btn-secondary text-sm">Export CSV</button>
              </div>
            </div>

            <div className="space-y-3">
              {filteredResults.map((r: any, i: number) => (
                <div key={r.candidate_id} className="card p-5 hover:shadow-md transition-shadow">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-1">
                        <span className="text-sm text-gray-400 font-mono">#{i + 1}</span>
                        <h3 className="font-semibold text-gray-900 text-lg">{r.full_name}</h3>
                        {r.extraction_confidence !== null && r.extraction_confidence < 0.6 && (
                          <span className="text-amber-500 text-sm" title="Low confidence extraction">Review</span>
                        )}
                      </div>
                      <p className="text-gray-600 text-sm mb-2">
                        {r.headline || `${r.current_role || ""} ${r.current_company ? `@ ${r.current_company}` : ""}`}
                        {r.location && <span className="ml-2 text-gray-400">{r.location}</span>}
                      </p>
                      <div className="space-y-1">
                        {r.match_explanation?.map((exp: string, j: number) => (
                          <p key={j} className="text-sm text-green-700 flex items-start gap-1">
                            <span className="text-green-500 mt-0.5">&#10003;</span> {exp}
                          </p>
                        ))}
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-2 ml-4">
                      <div className={cn("px-3 py-1.5 rounded-lg font-bold text-lg", scoreColor(r.match_score))}>
                        {Math.round(r.match_score)}%
                      </div>
                      <div className="text-xs text-gray-400">
                        S:{r.score_breakdown?.semantic} K:{r.score_breakdown?.skill} R:{r.score_breakdown?.role} E:{r.score_breakdown?.experience}
                      </div>
                      <select
                        value={r.candidate_status}
                        onChange={(e) => handleStatusChange(r.candidate_id, e.target.value)}
                        className="text-sm border rounded px-2 py-1"
                      >
                        {STATUS_OPTIONS.map((s) => (
                          <option key={s} value={s}>{STATUS_LABELS[s]}</option>
                        ))}
                      </select>
                      <Link href={`/candidates/${r.candidate_id}`} className="text-sm text-primary-600 hover:underline">
                        View Profile
                      </Link>
                    </div>
                  </div>
                </div>
              ))}
              {filteredResults.length === 0 && searchTrigger && !isLoading && (
                <div className="text-center py-12 text-gray-400">No candidates found for this search.</div>
              )}
            </div>
          </>
        )}

        {!data && !isLoading && (
          <div className="text-center py-20">
            <div className="w-20 h-20 bg-primary-50 rounded-full flex items-center justify-center mx-auto mb-4">
              <span className="text-3xl">&#128269;</span>
            </div>
            <h2 className="text-xl font-semibold text-gray-700 mb-2">Start searching</h2>
            <p className="text-gray-400 max-w-md mx-auto">
              Paste a job description or type a natural language query to find the best matching candidates.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
