import { useState } from 'react'
import { Download, FileUp } from 'lucide-react'
import { toast } from 'sonner'

import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import {
  useMyDocumentDownload,
  useMyDocumentRequests,
  useMyDocuments,
  useUploadMyDocument,
  useUploadRequestedDocument,
} from '@/hooks/useEmployeeSelf'
import { getErrorMessage } from '@/lib/errors'
import { formatDateTime, startCase } from '@/lib/format'
import { DOCUMENT_TYPE_OPTIONS } from '@/lib/constants'
import { getDocumentRequestStatusTone, getDocumentStatusTone } from '@/lib/status'
import type { DocumentType } from '@/types/hr'

export function DocumentsPage() {
  const { data, isLoading } = useMyDocuments()
  const { data: documentRequests } = useMyDocumentRequests()
  const uploadMutation = useUploadMyDocument()
  const uploadRequestedMutation = useUploadRequestedDocument()
  const downloadMutation = useMyDocumentDownload()

  const [documentType, setDocumentType] = useState<DocumentType>('PAN')
  const [file, setFile] = useState<File | null>(null)
  const [note, setNote] = useState('')
  const [requestFiles, setRequestFiles] = useState<Record<string, File | null>>({})
  const [uploadProgress, setUploadProgress] = useState(0)
  const [requestedUploadProgress, setRequestedUploadProgress] = useState<Record<string, number>>({})

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
        onUploadProgress: setUploadProgress,
      })
      toast.success('Document uploaded.')
      setFile(null)
      setNote('')
      setUploadProgress(0)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to upload document.'))
    }
  }

  const handleRequestedUpload = async (requestId: string) => {
    const requestedFile = requestFiles[requestId]
    if (!requestedFile) {
      toast.error('Choose a file before uploading.')
      return
    }
    try {
      await uploadRequestedMutation.mutateAsync({
        request_id: requestId,
        file: requestedFile,
        onUploadProgress: (progress) =>
          setRequestedUploadProgress((current) => ({ ...current, [requestId]: progress })),
      })
      toast.success('Requested document uploaded.')
      setRequestFiles((current) => ({ ...current, [requestId]: null }))
      setRequestedUploadProgress((current) => ({ ...current, [requestId]: 0 }))
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to upload requested document.'))
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
          description="Upload the documents your organisation requested and keep your broader employee record complete."
        />
      )}

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <SectionCard title="Requested onboarding documents" description="These requests come directly from your organisation admin and count toward onboarding completion.">
          {documentRequests && documentRequests.length > 0 ? (
            <div className="space-y-4">
              {documentRequests.map((request) => (
                <div key={request.id} className="surface-muted rounded-[24px] p-5">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-semibold text-[hsl(var(--foreground-strong))]">{request.document_type.name}</p>
                      <p className="text-sm text-[hsl(var(--muted-foreground))]">{request.document_type.category.replace(/_/g, ' ')}</p>
                    </div>
                    <StatusBadge tone={getDocumentRequestStatusTone(request.status)}>{request.status}</StatusBadge>
                  </div>
                  {request.rejection_note ? (
                    <p className="mt-3 text-sm text-[hsl(var(--danger))]">{request.rejection_note}</p>
                  ) : null}
                  <div className="mt-4 grid gap-3">
                    <input type="file" className="field-input" onChange={(event) => setRequestFiles((current) => ({ ...current, [request.id]: event.target.files?.[0] ?? null }))} />
                    <button type="button" className="btn-primary" onClick={() => void handleRequestedUpload(request.id)} disabled={uploadRequestedMutation.isPending}>
                      {uploadRequestedMutation.isPending && requestedUploadProgress[request.id]
                        ? `Uploading ${requestedUploadProgress[request.id]}%`
                        : 'Upload requested file'}
                    </button>
                    {requestedUploadProgress[request.id] ? (
                      <div className="h-2 overflow-hidden rounded-full bg-[hsl(var(--border)_/_0.65)]">
                        <div
                          className="h-full rounded-full bg-[linear-gradient(90deg,hsl(var(--brand)),hsl(var(--brand-strong)))]"
                          style={{ width: `${requestedUploadProgress[request.id]}%` }}
                        />
                      </div>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="No requested documents" description="There are no outstanding requested documents right now." icon={FileUp} />
          )}
        </SectionCard>

        <SectionCard title="Additional uploads" description="Use this for supporting documents that are useful to keep on file even if they were not explicitly requested.">
          <form onSubmit={handleUpload} className="grid gap-4">
            <div>
              <label className="field-label" htmlFor="document-type">
                Document type
              </label>
              <select id="document-type" className="field-select" value={documentType} onChange={(event) => setDocumentType(event.target.value as DocumentType)}>
                {DOCUMENT_TYPE_OPTIONS.map((type) => (
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
              <input id="document-file" type="file" className="field-input" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
            </div>
            <div>
              <label className="field-label" htmlFor="document-note">
                Note
              </label>
              <textarea id="document-note" className="field-textarea" value={note} onChange={(event) => setNote(event.target.value)} />
            </div>
            <button type="submit" className="btn-secondary" disabled={uploadMutation.isPending}>
              <FileUp className="h-4 w-4" />
              {uploadMutation.isPending && uploadProgress ? `Uploading ${uploadProgress}%` : 'Upload additional document'}
            </button>
            {uploadProgress ? (
              <div className="h-2 overflow-hidden rounded-full bg-[hsl(var(--border)_/_0.65)]">
                <div
                  className="h-full rounded-full bg-[linear-gradient(90deg,hsl(var(--brand)),hsl(var(--brand-strong)))]"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            ) : null}
          </form>

          <div className="mt-6">
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
                          <button type="button" className="btn-secondary" onClick={() => void handleDownload(document.id)}>
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
              <EmptyState title="No documents uploaded yet" description="Your uploads will appear here after you submit them." icon={FileUp} />
            )}
          </div>
        </SectionCard>
      </div>
    </div>
  )
}
