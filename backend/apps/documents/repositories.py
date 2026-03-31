from .models import Document


def list_documents(employee):
    return Document.objects.filter(employee=employee).order_by('-created_at')
