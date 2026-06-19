"use client";
import { useState, useCallback, useEffect, useRef } from "react";
import Navbar from "@/components/Navbar";
import { uploadPDFs, getBatchStatus } from "@/lib/api";
import { toast } from "sonner";
import { useDropzone } from "react-dropzone";

interface FileResult {
  filename: string;
  status: string;
  reason?: string | null;
  candidate_id?: string | null;
  is_update?: boolean;
}

export default function UploadPage() {
  const [batchId, setBatchId] = useState<string | null>(null);
  const [batchStatus, setBatchStatus] = useState<any>(null);
  const [uploading, setUploading] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const pdfs = acceptedFiles.filter((f) => f.name.toLowerCase().endsWith(".pdf"));
    if (!pdfs.length) return toast.error("Please upload PDF files only");

    setUploading(true);
    try {
      const data = await uploadPDFs(pdfs);
      setBatchId(data.batch_id);
      setBatchStatus({ total: data.files_received, processed: 0, succeeded: 0, failed: 0, status: "processing", files: [] });
      toast.success(`${data.files_received} files uploaded, processing started`);
    } catch {
      toast.error("Upload failed");
    } finally {
      setUploading(false);
    }
  }, []);

  useEffect(() => {
    if (!batchId || batchStatus?.status?.startsWith("completed")) return;

    intervalRef.current = setInterval(async () => {
      try {
        const status = await getBatchStatus(batchId);
        setBatchStatus(status);
        if (status.status.startsWith("completed")) {
          clearInterval(intervalRef.current!);
          toast.success(`Processing complete: ${status.succeeded} succeeded, ${status.failed} failed`);
        }
      } catch { /* ignore polling errors */ }
    }, 2000);

    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [batchId, batchStatus?.status]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    multiple: true,
  });

  const progressPct = batchStatus ? Math.round((batchStatus.processed / Math.max(batchStatus.total, 1)) * 100) : 0;

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Upload LinkedIn PDFs</h1>

        <div
          {...getRootProps()}
          className={`card p-12 border-2 border-dashed text-center cursor-pointer transition-colors ${
            isDragActive ? "border-primary-500 bg-primary-50" : "border-gray-300 hover:border-primary-400"
          }`}
        >
          <input {...getInputProps()} />
          <div className="w-16 h-16 bg-primary-50 rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-3xl">&#128196;</span>
          </div>
          {uploading ? (
            <p className="text-gray-600">Uploading files...</p>
          ) : isDragActive ? (
            <p className="text-primary-600 font-medium">Drop the PDFs here...</p>
          ) : (
            <>
              <p className="text-gray-700 font-medium">Drop LinkedIn PDFs here or click to browse</p>
              <p className="text-gray-400 text-sm mt-1">Accepts multiple .pdf files</p>
            </>
          )}
        </div>

        {batchStatus && (
          <div className="mt-8 space-y-4">
            <div className="card p-4">
              <div className="flex items-center justify-between mb-2">
                <h2 className="font-semibold text-gray-900">Processing Queue ({batchStatus.total} files)</h2>
                <span className={`text-sm font-medium ${batchStatus.status === "processing" ? "text-amber-600" : "text-green-600"}`}>
                  {batchStatus.status === "processing" ? "Processing..." : "Complete"}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3 mb-3">
                <div className="bg-primary-600 h-3 rounded-full transition-all duration-300" style={{ width: `${progressPct}%` }} />
              </div>
              <div className="flex gap-4 text-sm">
                <span className="text-green-600 font-medium">{batchStatus.succeeded} new</span>
                <span className="text-blue-600 font-medium">
                  {batchStatus.files?.filter((f: FileResult) => f.is_update).length || 0} updated
                </span>
                <span className="text-red-600 font-medium">{batchStatus.failed} failed</span>
                <span className="text-gray-400 ml-auto">{batchStatus.processed}/{batchStatus.total} processed</span>
              </div>
            </div>

            <div className="card divide-y divide-gray-100 max-h-96 overflow-y-auto">
              {batchStatus.files?.map((f: FileResult, i: number) => (
                <div key={i} className="px-4 py-3 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className={`text-lg ${f.status === "parsed" ? "text-green-500" : "text-red-500"}`}>
                      {f.status === "parsed" ? "✓" : "✗"}
                    </span>
                    <span className="text-sm text-gray-700 font-mono truncate max-w-xs">{f.filename}</span>
                  </div>
                  <div className="text-sm">
                    {f.status === "parsed" ? (
                      <span className={f.is_update ? "text-blue-600" : "text-green-600"}>
                        {f.is_update ? "Updated (v2+)" : "New candidate"}
                      </span>
                    ) : (
                      <span className="text-red-500">{f.reason || "Failed"}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
