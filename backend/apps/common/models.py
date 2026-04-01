from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from .current_actor import get_current_actor


class AuditedBaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )

    class Meta:
        abstract = True

    @property
    def modified_at(self):
        return self.updated_at

    @modified_at.setter
    def modified_at(self, value):
        self.updated_at = value

    @property
    def modified_by(self):
        return self.updated_by

    @modified_by.setter
    def modified_by(self, value):
        self.updated_by = value

    def save(self, *args, **kwargs):
        actor = get_current_actor()
        is_new = self._state.adding
        if actor is not None and getattr(actor, 'pk', None):
            if getattr(self, 'created_by_id', None) is None and is_new:
                self.created_by = actor
            self.updated_by = actor

            update_fields = kwargs.get('update_fields')
            if update_fields is not None:
                update_fields = set(update_fields)
                update_fields.discard('modified_at')
                update_fields.discard('modified_by')
                update_fields.add('updated_by')
                if is_new:
                    update_fields.add('created_by')
                kwargs['update_fields'] = update_fields

        super().save(*args, **kwargs)
