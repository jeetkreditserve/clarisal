from .models import Document


def list_documents(employee):
    return (
        Document.objects.filter(employee=employee)
        .select_related('uploaded_by', 'reviewed_by', 'document_request__document_type_ref')
        .order_by('-created_at')
    )
