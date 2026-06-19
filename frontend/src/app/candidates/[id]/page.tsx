"use client";
import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Navbar from "@/components/Navbar";
import { getCandidate, updateCandidate, addNote, getVersions } from "@/lib/api";
import { formatDate, formatExperience } from "@/lib/utils";
import { toast } from "sonner";

const STATUS_OPTIONS = ["new", "contacted", "shortlisted", "interview_scheduled", "rejected", "hired"];
const STATUS_LABELS: Record<string, string> = {
  new: "New", contacted: "Contacted", shortlisted: "Shortlisted",
  interview_scheduled: "Interview", rejected: "Rejected", hired: "Hired",
};

export default function CandidateProfilePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [noteText, setNoteText] = useState("");
  const [editing, setEditing] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const [showVersions, setShowVersions] = useState(false);

  const { data: candidate, isLoading } = useQuery({
    queryKey: ["candidate", id],
    queryFn: () => getCandidate(id),
    enabled: !!id,
  });

  const { data: versionsData } = useQuery({
    queryKey: ["versions", id],
    queryFn: () => getVersions(id),
    enabled: !!id && showVersions,
  });

  const handleStatusChange = async (status: string) => {
    try {
      await updateCandidate(id, { candidate_status: status });
      queryClient.invalidateQueries({ queryKey: ["candidate", id] });
      toast.success("Status updated");
    } catch {
      toast.error("Update failed");
    }
  };

  const handleFieldSave = async (field: string) => {
    try {
      await updateCandidate(id, { [field]: editValue });
      queryClient.invalidateQueries({ queryKey: ["candidate", id] });
      setEditing(null);
      toast.success("Saved");
    } catch {
      toast.error("Save failed");
    }
  };

  const handleAddNote = async () => {
    if (!noteText.trim()) return;
    try {
      await addNote(id, noteText);
      queryClient.invalidateQueries({ queryKey: ["candidate", id] });
      setNoteText("");
      toast.success("Note added");
    } catch {
      toast.error("Failed to add note");
    }
  };

  const startEdit = (field: string, value: string) => {
    setEditing(field);
    setEditValue(value || "");
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="flex items-center justify-center py-20 text-gray-400">Loading...</div>
      </div>
    );
  }

  if (!candidate) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="flex items-center justify-center py-20 text-gray-400">Candidate not found</div>
      </div>
    );
  }

  const EditableField = ({ field, value, label }: { field: string; value: string | null; label: string }) => (
    <div className="group">
      {editing === field ? (
        <div className="flex gap-2">
          <input
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            className="input-field text-sm flex-1"
            autoFocus
            onKeyDown={(e) => { if (e.key === "Enter") handleFieldSave(field); if (e.key === "Escape") setEditing(null); }}
          />
          <button onClick={() => handleFieldSave(field)} className="text-sm text-primary-600">Save</button>
          <button onClick={() => setEditing(null)} className="text-sm text-gray-400">Cancel</button>
        </div>
      ) : (
        <span
          onClick={() => startEdit(field, value || "")}
          className="cursor-pointer hover:bg-primary-50 px-1 py-0.5 rounded transition-colors"
          title={`Click to edit ${label}`}
        >
          {value || <span className="text-gray-300 italic">Click to add {label}</span>}
        </span>
      )}
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <button onClick={() => router.back()} className="text-sm text-primary-600 hover:underline mb-4 inline-block">
          &larr; Back
        </button>

        {/* Header */}
        <div className="card p-6 mb-6">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h1 className="text-2xl font-bold text-gray-900 mb-1">
                <EditableField field="full_name" value={candidate.full_name} label="name" />
              </h1>
              <p className="text-gray-600">
                <EditableField field="headline" value={candidate.headline} label="headline" />
              </p>
              <div className="flex flex-wrap gap-4 mt-3 text-sm text-gray-500">
                {candidate.location && <span>&#128205; {candidate.location}</span>}
                {candidate.email && <span>&#9993; {candidate.email}</span>}
                {candidate.phone && <span>&#128222; {candidate.phone}</span>}
                {candidate.linkedin_url && (
                  <a href={`https://${candidate.linkedin_url}`} target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:underline">
                    LinkedIn
                  </a>
                )}
              </div>
              <div className="flex items-center gap-4 mt-3">
                <span className="text-sm text-gray-400">Experience: {formatExperience(candidate.total_experience_months)}</span>
                <span className="text-sm text-gray-400">Version {candidate.current_version}</span>
                {candidate.extraction_confidence !== null && candidate.extraction_confidence < 0.6 && (
                  <span className="text-amber-500 text-sm">Low confidence — review recommended</span>
                )}
              </div>
            </div>
            <div className="ml-4">
              <select
                value={candidate.candidate_status}
                onChange={(e) => handleStatusChange(e.target.value)}
                className="input-field text-sm"
              >
                {STATUS_OPTIONS.map((s) => (
                  <option key={s} value={s}>{STATUS_LABELS[s]}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* About */}
        <div className="card p-6 mb-6">
          <h2 className="font-semibold text-gray-900 mb-3">About</h2>
          <EditableField field="summary" value={candidate.summary} label="summary" />
        </div>

        {/* Experience */}
        <div className="card p-6 mb-6">
          <h2 className="font-semibold text-gray-900 mb-3">Experience</h2>
          {candidate.experiences?.length > 0 ? (
            <div className="space-y-4">
              {candidate.experiences.map((exp: any) => (
                <div key={exp.id} className="border-l-2 border-primary-200 pl-4">
                  <p className="font-medium text-gray-900">{exp.role || "Role not specified"}</p>
                  <p className="text-sm text-gray-600">{exp.company}</p>
                  <p className="text-xs text-gray-400">
                    {formatDate(exp.start_date)} — {exp.end_date ? formatDate(exp.end_date) : "Present"}
                  </p>
                  {exp.description && <p className="text-sm text-gray-500 mt-1">{exp.description}</p>}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-300 italic">No experience data</p>
          )}
        </div>

        {/* Education */}
        <div className="card p-6 mb-6">
          <h2 className="font-semibold text-gray-900 mb-3">Education</h2>
          {candidate.education_entries?.length > 0 ? (
            <div className="space-y-3">
              {candidate.education_entries.map((edu: any) => (
                <div key={edu.id} className="border-l-2 border-gray-200 pl-4">
                  <p className="font-medium text-gray-900">{edu.degree} {edu.field ? `in ${edu.field}` : ""}</p>
                  <p className="text-sm text-gray-600">{edu.institution}</p>
                  <p className="text-xs text-gray-400">
                    {edu.start_date ? formatDate(edu.start_date) : ""} {edu.end_date ? `— ${formatDate(edu.end_date)}` : ""}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-300 italic">No education data</p>
          )}
        </div>

        {/* Skills */}
        <div className="card p-6 mb-6">
          <h2 className="font-semibold text-gray-900 mb-3">Skills</h2>
          {candidate.skills?.length > 0 ? (
            <div>
              <div className="flex flex-wrap gap-2 mb-2">
                {[...new Set(candidate.skills.flatMap((s: any) => s.normalized_skills || []))].map((skill: string) => (
                  <span key={skill} className="px-2.5 py-1 bg-primary-50 text-primary-700 rounded-full text-sm font-medium">
                    {skill}
                  </span>
                ))}
              </div>
              <p className="text-xs text-gray-400 mt-2">
                Originally listed as: {candidate.skills.map((s: any) => s.original_skill).join(", ")}
              </p>
            </div>
          ) : (
            <p className="text-gray-300 italic">No skills data</p>
          )}
        </div>

        {/* Notes */}
        <div className="card p-6 mb-6">
          <h2 className="font-semibold text-gray-900 mb-3">Notes</h2>
          {candidate.notes?.length > 0 && (
            <div className="space-y-2 mb-4">
              {candidate.notes.map((n: any) => (
                <div key={n.id} className="bg-gray-50 p-3 rounded-lg">
                  <p className="text-sm text-gray-700">{n.note_text}</p>
                  <p className="text-xs text-gray-400 mt-1">{formatDate(n.created_at)}</p>
                </div>
              ))}
            </div>
          )}
          <div className="flex gap-2">
            <input
              type="text"
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              placeholder="Add a note..."
              className="input-field flex-1"
              onKeyDown={(e) => { if (e.key === "Enter") handleAddNote(); }}
            />
            <button onClick={handleAddNote} className="btn-primary text-sm">Add Note</button>
          </div>
        </div>

        {/* Version History */}
        <div className="card p-6 mb-6">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-gray-900">Version History</h2>
            <button onClick={() => setShowVersions(!showVersions)} className="text-sm text-primary-600 hover:underline">
              {showVersions ? "Hide" : "Show"}
            </button>
          </div>
          {showVersions && versionsData?.versions && (
            <div className="space-y-3">
              {versionsData.versions.map((v: any) => (
                <div key={v.version_number} className="border-l-2 border-gray-200 pl-4">
                  <p className="font-medium text-gray-700 text-sm">Version {v.version_number} — {formatDate(v.created_at)}</p>
                  {v.changes_summary?.map((change: string, i: number) => (
                    <p key={i} className="text-sm text-gray-500 ml-2">{change}</p>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
