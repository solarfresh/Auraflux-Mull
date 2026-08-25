from django.db import models
from django.utils.translation import gettext_lazy as _


class AgentOutputFormat(models.TextChoices):
    JSON = 'JSON', _('JSON')
    TEXT = 'TEXT', _('TEXT')
