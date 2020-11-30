# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
import locale

from django.contrib.postgres.fields.jsonb import JSONField as PostgresJSONField
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from cosinnus.conf import settings
from django.urls.base import reverse


# this reads the environment and inits the right locale
try:
    locale.setlocale(locale.LC_ALL, ("de_DE", "utf8"))
except:
    locale.setlocale(locale.LC_ALL, "")


@python_2_unicode_compatible
class CosinnusUserImport(models.Model):
    """ Saves uploaded import data and report output so that a dry-run can be saved and the user can,
        after checking the report, finalize the import from the dry run.
        After importing, this saves as a log for the import.
        There should only ever be one CosinnusUserImport object with ANY state other than STATE_ARCHIVED! """
    
    STATE_DRY_RUN_RUNNING = 0
    STATE_DRY_RUN_FINISHED_INVALID = 1
    STATE_DRY_RUN_FINISHED_VALID = 2
    STATE_IMPORT_RUNNING = 3
    STATE_IMPORT_FINISHED = 4
    STATE_ARCHIVED = 5
    
    #: Choices for :attr:`state`: ``(int, str)``
    STATE_CHOICES = (
        (STATE_DRY_RUN_RUNNING, _('Dry run in progress')),
        (STATE_DRY_RUN_FINISHED_INVALID, _('Dry run finished, errors in CSV that prevent import')),
        (STATE_DRY_RUN_FINISHED_VALID, _('Dry run finished, waiting to start import')),
        (STATE_IMPORT_RUNNING, _('Import running')),
        (STATE_IMPORT_FINISHED, _('Import finished')),
        (STATE_ARCHIVED, _('Import archived')),
    )
    
    last_modified = models.DateTimeField(
        verbose_name=_('Last modified'),
        editable=False,
        auto_now=True)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL,
        verbose_name=_('Creator'),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+')
    
    state = models.PositiveSmallIntegerField(_('Import state'), blank=False,
        default=STATE_DRY_RUN_RUNNING, choices=STATE_CHOICES, editable=False)
    
    import_data = PostgresJSONField(default=dict, verbose_name=_('Import Data'), blank=True,
        help_text='Stores the uploaded CSV data',
        encoder=DjangoJSONEncoder, editable=False)
    import_report_html = models.TextField(verbose_name=_('Import Report HTML'),
       help_text='Stores the generated report for what the import will do / has done.', blank=True)
    
    
    class Meta(object):
        ordering = ('-last_modified',)
        verbose_name = _('Cosinnus User Import')
        verbose_name_plural = _('Cosinnus User Imports')

    def __init__(self, *args, **kwargs):
        super(CosinnusUserImport, self).__init__(*args, **kwargs)

    def __str__(self):
        return f'<UserImport from {self.last_modified}>'
    
    def save(self, *args, **kwargs):
        # sanity check: if the to-be-saved state isn't STATE_ARCHIVED, make sure no other import exists that isn't archived
        if self.state != CosinnusUserImport.STATE_ARCHIVED:
            created = bool(self.pk is None)
            existing_imports = CosinnusUserImport.objects.exclude(state=CosinnusUserImport.STATE_ARCHIVED)
            if not created:
                existing_imports.exclude(id=self.id)
            if existing_imports.count() > 0:
                raise Exception('CosinnusUserImport: Could not save import object because state check failed: there is another import that is not archived.')
        super(CosinnusUserImport, self).save(*args, **kwargs)
        
    def get_absolute_url(self):
        return reverse('cosinnus:administration-archived-user-import', kwargs={'pk': self.import_object.id})
