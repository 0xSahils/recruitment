"use client";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Navbar from "@/components/Navbar";
import { getCandidates, exportCandidates, deleteCandidate } from "@/lib/api";
import { formatExperience, formatDate } from "@/lib/utils";
import { toast } from "sonner";
import Link from "next/link";

const STATUS_LABELS: Record<string, string> = {
  new: "New", contacted: "Contacted", shortlisted: "Shortlisted",
  interview_scheduled: "Interview", rejected: "Rejected", hired: "Hired",
};

const STATUS_COLORS: Record<string, string> = {
  new: "bg-blue-100 text-blue-700",
  contacted: "bg-purple-100 text-purple-700",
  shortlisted: "bg-green-100 text-green-700",
  interview_scheduled: "bg-amber-100 text-amber-700",
  rejected: "bg-red-100 text-red-700",
  hired: "bg-emerald-100 text-emerald-700",
};

export default function CandidatesPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [locationFilter, setLocationFilter] = useState("");
  const [search, setSearch] = useState("");

  const params: Record<string, string | number> = { page, page_size: 50 };
  if (statusFilter) params.status = statusFilter;
  if (locationFilter) params.location = locationFilter;
  if (search) params.search = search;

  const { data, isLoading } = useQuery({
    queryKey: ["candidates", page, statusFilter, locationFilter, search],
    queryFn: () => getCandidates(params),
  });

  const handleExport = async () => {
    try {
      const filters: Record<string, string> = {};
      if (statusFilter) filters.status = statusFilter;
      if (locationFilter) filters.location = locationFilter;
      await exportCandidates({ filters });
      toast.success("CSV exported");
    } catch {
      toast.error("Export failed");
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Delete ${name}?`)) return;
    try {
      await deleteCandidate(id);
      queryClient.invalidateQueries({ queryKey: ["candidates"] });
      toast.success(`${name} deleted`);
    } catch {
      toast.error("Delete failed");
    }
  };

  const candidates = data?.candidates || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / 50);

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-900">All Candidates ({total})</h1>
          <div className="flex gap-2">
            <button onClick={handleExport} className="btn-secondary text-sm">Export CSV</button>
            <button
              onClick={async () => {
                if (!confirm(`Delete all ${total} candidates? This cannot be undone.`)) return;
                try {
                  for (const c of candidates) {
                    await deleteCandidate(c.id);
                  }
                  queryClient.invalidateQueries({ queryKey: ["candidates"] });
                  toast.success("All candidates deleted");
                } catch {
                  toast.error("Some deletions failed");
                  queryClient.invalidateQueries({ queryKey: ["candidates"] });
                }
              }}
              className="text-sm text-red-500 hover:text-red-700 hover:bg-red-50 px-3 py-1.5 rounded-lg border border-red-200 transition-colors"
            >
              Delete All
            </button>
          </div>
        </div>

        <div className="card p-4 mb-6 flex flex-wrap gap-3">
          <input
            type="text"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            placeholder="Search by name, role, company..."
            className="input-field flex-1 min-w-[200px]"
          />
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            className="input-field w-auto"
          >
            <option value="">All Statuses</option>
            {Object.entries(STATUS_LABELS).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
          <input
            type="text"
            value={locationFilter}
            onChange={(e) => { setLocationFilter(e.target.value); setPage(1); }}
            placeholder="Filter by location..."
            className="input-field w-auto max-w-xs"
          />
        </div>

        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50 border-b">
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Headline</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Location</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Experience</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Updated</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {candidates.map((c: any) => (
                  <tr key={c.id} className="hover:bg-gray-50 cursor-pointer">
                    <td className="px-4 py-3">
                      <Link href={`/candidates/${c.id}`} className="text-primary-600 hover:underline font-medium">
                        {c.full_name}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600 max-w-xs truncate">{c.headline || "-"}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{c.location || "-"}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{formatExperience(c.total_experience_months)}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[c.candidate_status] || ""}`}>
                        {STATUS_LABELS[c.candidate_status] || c.candidate_status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-400">{formatDate(c.updated_at)}</td>
                    <td className="px-4 py-3">
                      <button
                        onClick={(e) => { e.preventDefault(); handleDelete(c.id, c.full_name); }}
                        className="text-xs text-red-400 hover:text-red-600"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
                {!isLoading && candidates.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-12 text-center text-gray-400">
                      No candidates found. Upload some PDFs first.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t">
              <button
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
                className="btn-secondary text-sm disabled:opacity-50"
              >
                Previous
              </button>
              <span className="text-sm text-gray-500">Page {page} of {totalPages}</span>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage(page + 1)}
                className="btn-secondary text-sm disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
