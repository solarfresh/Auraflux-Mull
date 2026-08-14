from django.db import models
from django.utils.translation import gettext_lazy as _


class ImpactLevel(models.TextChoices):
    STRATEGIC = 'strategic', _('Strategic')
    TACTICAL = 'tactical', _('Tactical')
    OPERATIONAL = 'operational', _('Operational')


class SupportedFileType(models.TextChoices):
    PDF = 'pdf', _('PDF')
    DOCX = 'docx', _('DOCX')
    TXT = 'txt', _('TXT')
    CSV = 'csv', _('CSV')
