import { useState } from 'react'
import { Download, FileUp } from 'lucide-react'
import { toast } from 'sonner'
import { useMyDocumentDownload, useMyDocuments, useUploadMyDocument } from '@/hooks/useEmployeeSelf'
import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { formatDateTime, startCase } from '@/lib/format'
import { getErrorMessage } from '@/lib/errors'
import { getDocumentStatusTone } from '@/lib/status'
import type { DocumentType } from '@/types/hr'

const documentTypes: DocumentType[] = ['PAN', 'AADHAAR', 'EDUCATION_CERT', 'EMPLOYMENT_LETTER', 'OTHER']

export function DocumentsPage() {
  const { data, isLoading } = useMyDocuments()
  const uploadMutation = useUploadMyDocument()
  const downloadMutation = useMyDocumentDownload()

  const [documentType, setDocumentType] = useState<DocumentType>('PAN')
  const [file, setFile] = useState<File | null>(null)
  const [note, setNote] = useState('')

  const handleUpload = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!file) {
      toast.error('Choose a file before uploading.')
      return
    }
    try {
      await uploadMutation.mutateAsync({
        document_type: documentType,
        file,
        metadata: note ? { note } : undefined,
      })
      toast.success('Document uploaded.')
      setFile(null)
      setNote('')
      const fileInput = document.getElementById('document-file') as HTMLInputElement | null
      if (fileInput) fileInput.value = ''
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to upload document.'))
    }
  }

  const handleDownload = async (documentId: string) => {
    try {
      const response = await downloadMutation.mutateAsync(documentId)
      window.open(response.url, '_blank', 'noopener,noreferrer')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to open document.'))
    }
  }

  return (
    <div className="space-y-6">
      {isLoading && !data ? (
        <SkeletonPageHeader />
      ) : (
        <PageHeader
          eyebrow="Documents"
          title="My documents"
          description="Upload PAN, Aadhaar, education, or other onboarding documents for verification."
        />
      )}

      <div className="grid gap-6 xl:grid-cols-[0.85fr_1.15fr]">
        <SectionCard title="Upload document" description="Files are stored privately and shared through secure signed links.">
          <form onSubmit={handleUpload} className="grid gap-4">
            <div>
              <label className="field-label" htmlFor="document-type">
                Document type
              </label>
              <select
                id="document-type"
                className="field-select"
                value={documentType}
                onChange={(event) => setDocumentType(event.target.value as DocumentType)}
              >
                {documentTypes.map((type) => (
                  <option key={type} value={type}>
                    {startCase(type)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="field-label" htmlFor="document-file">
                File
              </label>
              <input
                id="document-file"
                type="file"
                className="field-input"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                required
              />
            </div>
            <div>
              <label className="field-label" htmlFor="document-note">
                Note
              </label>
              <textarea
                id="document-note"
                className="field-textarea"
                value={note}
                onChange={(event) => setNote(event.target.value)}
                placeholder="Optional context for the reviewer"
              />
            </div>
            <div className="notice-info">
              Upload clear scans or PDFs. Review status updates are reflected here after your organisation administrator verifies or rejects the file.
            </div>
            <button type="submit" className="btn-primary" disabled={uploadMutation.isPending}>
              <FileUp className="h-4 w-4" />
              {uploadMutation.isPending ? 'Uploading...' : 'Upload document'}
            </button>
          </form>
        </SectionCard>

        <SectionCard title="Uploaded documents" description="Track review progress and re-open approved or rejected files.">
          {isLoading ? (
            <SkeletonTable rows={4} />
          ) : data && data.length > 0 ? (
            <div className="table-shell">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="table-head-row">
                    <th className="pb-3 pr-4 font-semibold">Document</th>
                    <th className="pb-3 pr-4 font-semibold">Status</th>
                    <th className="pb-3 pr-4 font-semibold">Uploaded</th>
                    <th className="pb-3 text-right font-semibold">Action</th>
                  </tr>
                </thead>
                <tbody className="table-body">
                  {data.map((document) => (
                    <tr key={document.id} className="table-row border-b border-[hsl(var(--border)_/_0.76)] last:border-b-0">
                      <td className="py-4 pr-4">
                        <p className="table-primary font-semibold">{startCase(document.document_type)}</p>
                        <p className="table-secondary mt-1 text-xs">{document.file_name}</p>
                      </td>
                      <td className="py-4 pr-4">
                        <StatusBadge tone={getDocumentStatusTone(document.status)}>{document.status}</StatusBadge>
                      </td>
                      <td className="table-secondary py-4 pr-4">{formatDateTime(document.created_at)}</td>
                      <td className="py-4 text-right">
                        <button type="button" className="btn-secondary" onClick={() => handleDownload(document.id)}>
                          <Download className="h-4 w-4" />
                          Open
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              title="No documents uploaded yet"
              description="Upload your first onboarding document so your administrator can begin verification."
              icon={FileUp}
            />
          )}
        </SectionCard>
      </div>
    </div>
  )
}
