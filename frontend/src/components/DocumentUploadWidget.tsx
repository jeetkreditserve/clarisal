import { useId, useState, type ChangeEvent } from 'react'

import { useUploadMyDocument } from '@/hooks/useEmployeeSelf'
import { getErrorMessage } from '@/lib/errors'
import type { DocumentRecord } from '@/types/hr'

interface DocumentUploadWidgetProps {
  id?: string
  label: string
  accept?: string
  documentType?: string
  existingFileName?: string | null
  existingDownloadUrl?: string | null
  onUpload: (document: DocumentRecord) => void | Promise<void>
}

export function DocumentUploadWidget({
  id,
  label,
  accept = '.pdf,.png,.jpg,.jpeg',
  documentType = 'OTHER',
  existingFileName,
  existingDownloadUrl,
  onUpload,
}: DocumentUploadWidgetProps) {
  const fallbackId = useId()
  const inputId = id ?? `document-upload-${fallbackId}`
  const uploadMutation = useUploadMyDocument()
  const [error, setError] = useState<string | null>(null)
  const [progress, setProgress] = useState(0)
  const [uploadedDocument, setUploadedDocument] = useState<DocumentRecord | null>(null)

  const activeDocument = uploadedDocument
  const fileName = activeDocument?.file_name ?? existingFileName ?? null
  const downloadUrl = activeDocument?.metadata?.download_url
  const resolvedDownloadUrl = typeof downloadUrl === 'string' ? downloadUrl : existingDownloadUrl

  const handleFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    setError(null)
    setProgress(0)
    try {
      const document = await uploadMutation.mutateAsync({
        document_type: documentType,
        file,
        metadata: { source: 'INVESTMENT_DECLARATION_PROOF' },
        onUploadProgress: setProgress,
      })
      setUploadedDocument(document)
      await onUpload(document)
    } catch (uploadError) {
      setError(getErrorMessage(uploadError, 'Unable to upload the proof document.'))
    } finally {
      event.target.value = ''
      setProgress(0)
    }
  }

  return (
    <div className="grid gap-3">
      <label className="field-label" htmlFor={inputId}>
        {label}
      </label>
      {fileName ? (
        <div className="surface-muted flex flex-wrap items-center justify-between gap-3 rounded-[18px] px-4 py-3">
          <div>
            <p className="font-medium text-[hsl(var(--foreground-strong))]">{fileName}</p>
            {resolvedDownloadUrl ? (
              <a
                href={resolvedDownloadUrl}
                target="_blank"
                rel="noreferrer"
                className="mt-1 inline-flex text-sm text-[hsl(var(--brand))] hover:text-[hsl(var(--brand-strong))]"
              >
                Download current proof
              </a>
            ) : null}
          </div>
          <label className="btn-secondary cursor-pointer">
            Change
            <input
              id={inputId}
              type="file"
              accept={accept}
              className="sr-only"
              aria-label={label}
              onChange={(event) => void handleFileChange(event)}
            />
          </label>
        </div>
      ) : (
        <input
          id={inputId}
          type="file"
          accept={accept}
          className="field-input"
          onChange={(event) => void handleFileChange(event)}
        />
      )}
      {uploadMutation.isPending ? (
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          Uploading{progress ? ` ${progress}%` : '...'}
        </p>
      ) : null}
      {error ? <p className="text-sm text-[hsl(var(--danger))]">{error}</p> : null}
    </div>
  )
}
