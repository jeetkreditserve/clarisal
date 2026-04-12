import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { DocumentUploadWidget } from '@/components/DocumentUploadWidget'

const useUploadMyDocument = vi.fn()

vi.mock('@/hooks/useEmployeeSelf', () => ({
  useUploadMyDocument: () => useUploadMyDocument(),
}))

describe('DocumentUploadWidget', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useUploadMyDocument.mockReturnValue({
      isPending: false,
      mutateAsync: vi.fn().mockResolvedValue({
        id: 'doc-1',
        document_type: 'OTHER',
        document_type_code: 'OTHER',
        document_request: null,
        file_name: 'proof.pdf',
        file_size: 128,
        mime_type: 'application/pdf',
        status: 'PENDING',
        metadata: {},
        version: 1,
        expiry_date: null,
        alert_days_before: 30,
        expires_soon: false,
        uploaded_by_email: 'employee@test.com',
        reviewed_by_email: null,
        reviewed_at: null,
        created_at: '2026-04-01T00:00:00Z',
      }),
    })
  })

  it('renders a file input and calls onUpload with the uploaded document', async () => {
    const user = userEvent.setup()
    const onUpload = vi.fn()

    render(<DocumentUploadWidget label="Proof document" onUpload={onUpload} />)

    const input = screen.getByLabelText('Proof document')
    expect(input).toHaveAttribute('type', 'file')

    await user.upload(input, new File(['proof'], 'proof.pdf', { type: 'application/pdf' }))

    await waitFor(() => {
      expect(onUpload).toHaveBeenCalledWith(expect.objectContaining({ id: 'doc-1', file_name: 'proof.pdf' }))
    })
  })

  it('renders an inline error when the upload fails', async () => {
    const user = userEvent.setup()
    useUploadMyDocument.mockReturnValue({
      isPending: false,
      mutateAsync: vi.fn().mockRejectedValue(new Error('upload failed')),
    })

    render(<DocumentUploadWidget label="Proof document" onUpload={vi.fn()} />)

    await user.upload(screen.getByLabelText('Proof document'), new File(['proof'], 'proof.pdf', { type: 'application/pdf' }))

    expect(await screen.findByText('Unable to upload the proof document.')).toBeInTheDocument()
  })

  it('shows the existing proof filename and download link', () => {
    render(
      <DocumentUploadWidget
        label="Proof document"
        existingFileName="existing-proof.pdf"
        existingDownloadUrl="https://example.com/proof.pdf"
        onUpload={vi.fn()}
      />
    )

    expect(screen.getByText('existing-proof.pdf')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Download current proof' })).toHaveAttribute('href', 'https://example.com/proof.pdf')
  })
})
