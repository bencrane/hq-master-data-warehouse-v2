'use client';

import { useState, useCallback } from 'react';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { uploadTargetClients, TargetClientRow, UploadResult } from "@/app/actions/upload-target-clients";

function parseCSV(text: string): TargetClientRow[] {
  const lines = text.trim().split('\n');
  if (lines.length < 2) return [];

  const headers = lines[0].split(',').map(h => h.trim().toLowerCase().replace(/['"]/g, ''));
  
  // Map common header variations
  const headerMap: Record<string, keyof TargetClientRow> = {
    'company_name': 'company_name',
    'company name': 'company_name',
    'companyname': 'company_name',
    'name': 'company_name',
    'domain': 'domain',
    'website': 'domain',
    'company_linkedin_url': 'company_linkedin_url',
    'linkedin_url': 'company_linkedin_url',
    'linkedin': 'company_linkedin_url',
    'slug': 'slug',
  };

  const columnIndices: Partial<Record<keyof TargetClientRow, number>> = {};
  headers.forEach((header, idx) => {
    const mapped = headerMap[header];
    if (mapped) {
      columnIndices[mapped] = idx;
    }
  });

  const rows: TargetClientRow[] = [];
  for (let i = 1; i < lines.length; i++) {
    const values = lines[i].split(',').map(v => v.trim().replace(/^["']|["']$/g, ''));
    if (values.length === 0 || values.every(v => !v)) continue;

    const row: TargetClientRow = {
      company_name: columnIndices.company_name !== undefined ? values[columnIndices.company_name] : '',
      domain: columnIndices.domain !== undefined ? values[columnIndices.domain] : '',
      company_linkedin_url: columnIndices.company_linkedin_url !== undefined ? values[columnIndices.company_linkedin_url] : undefined,
      slug: columnIndices.slug !== undefined ? values[columnIndices.slug] : undefined,
    };
    rows.push(row);
  }

  return rows;
}

export default function UploadTargetClientsPage() {
  const [rows, setRows] = useState<TargetClientRow[]>([]);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [fileName, setFileName] = useState<string>('');

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setFileName(file.name);
    setResult(null);

    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      const parsed = parseCSV(text);
      setRows(parsed);
    };
    reader.readAsText(file);
  }, []);

  const handleUpload = async () => {
    if (rows.length === 0) return;
    
    setIsUploading(true);
    try {
      const uploadResult = await uploadTargetClients(rows);
      setResult(uploadResult);
      if (uploadResult.success) {
        setRows([]);
        setFileName('');
      }
    } catch (err) {
      setResult({ success: false, inserted: 0, errors: [`Upload failed: ${err}`] });
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="container mx-auto p-10 max-w-5xl">
      <Card>
        <CardHeader>
          <CardTitle>Upload Target Clients</CardTitle>
          <CardDescription>
            Upload a CSV file with columns: company_name, domain, company_linkedin_url (optional), slug (optional)
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* File Upload */}
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
            <input
              type="file"
              accept=".csv"
              onChange={handleFileChange}
              className="hidden"
              id="csv-upload"
            />
            <label
              htmlFor="csv-upload"
              className="cursor-pointer flex flex-col items-center gap-2"
            >
              <svg className="w-10 h-10 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <span className="text-sm text-gray-600">
                {fileName || 'Click to upload CSV'}
              </span>
            </label>
          </div>

          {/* Preview Table */}
          {rows.length > 0 && (
            <div>
              <h3 className="font-medium mb-2">Preview ({rows.length} rows)</h3>
              <div className="border rounded-lg overflow-hidden max-h-80 overflow-y-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Company Name</TableHead>
                      <TableHead>Domain</TableHead>
                      <TableHead>LinkedIn URL</TableHead>
                      <TableHead>Slug</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {rows.slice(0, 20).map((row, idx) => (
                      <TableRow key={idx}>
                        <TableCell className="font-medium">{row.company_name || <span className="text-red-500">Missing</span>}</TableCell>
                        <TableCell>{row.domain || <span className="text-red-500">Missing</span>}</TableCell>
                        <TableCell className="text-sm text-gray-500 truncate max-w-[200px]">{row.company_linkedin_url || '-'}</TableCell>
                        <TableCell className="text-sm">{row.slug || <span className="text-gray-400">Auto</span>}</TableCell>
                      </TableRow>
                    ))}
                    {rows.length > 20 && (
                      <TableRow>
                        <TableCell colSpan={4} className="text-center text-gray-500">
                          ... and {rows.length - 20} more rows
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </div>
          )}

          {/* Result Messages */}
          {result && (
            <div className={`p-4 rounded-lg ${result.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
              {result.success ? (
                <p className="text-green-800">✓ Successfully inserted {result.inserted} clients</p>
              ) : (
                <div>
                  <p className="text-red-800 font-medium">Inserted {result.inserted} clients with {result.errors.length} errors:</p>
                  <ul className="mt-2 text-sm text-red-700 list-disc list-inside max-h-40 overflow-y-auto">
                    {result.errors.map((err, idx) => (
                      <li key={idx}>{err}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Upload Button */}
          <div className="flex gap-3">
            <Button
              onClick={handleUpload}
              disabled={rows.length === 0 || isUploading}
            >
              {isUploading ? 'Uploading...' : `Upload ${rows.length} Clients`}
            </Button>
            {rows.length > 0 && (
              <Button
                variant="outline"
                onClick={() => { setRows([]); setFileName(''); setResult(null); }}
              >
                Clear
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

