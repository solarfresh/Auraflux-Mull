from django.db import models
from django.utils.translation import gettext_lazy as _


class EntityStatus(models.TextChoices):
    # Under active editing by the user
    DRAFT = 'DRAFT', _('Draft')

    # Proposed by the AI Agent, awaiting user review
    REVIEW = 'REVIEW', _('Review')

    # Finalized and protected from accidental changes
    LOCKED = 'LOCKED', _('Locked')

    # Temporarily sidelined from the active map or focus
    ON_HOLD = 'ON_HOLD', _('On Hold')

    # Removed from view but preserved in history
    ARCHIVED = 'ARCHIVED', _('Archived')

    # Awaiting approval or further action
    PENDING = 'PENDING', _('Pending')

    # Approved and ready for use
    APPROVED = 'APPROVED', _('Approved')

    # Not approved and requires changes
    REJECTED = 'REJECTED', _('Rejected')

    # Made publicly available
    PUBLISHED = 'PUBLISHED', _('Published')

    # Currently in use or operational
    ACTIVE = 'ACTIVE', _('Active')

    # Not currently in use but can be reactivated
    INACTIVE = 'INACTIVE', _('Inactive')

    # Marked for deletion and no longer accessible
    DELETED = 'DELETED', _('Deleted')


class ProcessStatus(models.TextChoices):
    IDLE = 'IDLE', _('Idle')
    QUEUED = 'QUEUED', _('Queued')
    PROCESSING = 'PROCESSING', _('Processing')
    SUCCESS = 'SUCCESS', _('Success')
    ERROR = 'ERROR', _('Error')
    CANCELLED = 'CANCELLED', _('Cancelled')
    PAUSED = 'PAUSED', _('Paused')
