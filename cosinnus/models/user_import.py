# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
import locale
from threading import Thread

from django.contrib.postgres.fields.jsonb import JSONField as PostgresJSONField
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.urls.base import reverse
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from cosinnus.conf import settings
from cosinnus.utils.functions import resolve_class
import logging

logger = logging.getLogger('cosinnus')


# this reads the environment and inits the right locale
try:
    locale.setlocale(locale.LC_ALL, ("de_DE", "utf8"))
except:
    locale.setlocale(locale.LC_ALL, "")


class CosinnusUserImportReportItems(object):
    
    text = None
    report_class = "info"
    
    def __init__(self, text, report_class="info"):
        self.text = text
        self.report_class = report_class
        
    def to_string(self):
        return f'<div class="report-item {self.report_class}">{self.text}</div>'


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
    STATE_IMPORT_FAILED = 5
    STATE_ARCHIVED = 6
    
    #: Choices for :attr:`state`: ``(int, str)``
    STATE_CHOICES = (
        (STATE_DRY_RUN_RUNNING, _('Dry run in progress')),
        (STATE_DRY_RUN_FINISHED_INVALID, _('Dry run finished, errors in CSV that prevent import')),
        (STATE_DRY_RUN_FINISHED_VALID, _('Dry run finished, waiting to start import')),
        (STATE_IMPORT_RUNNING, _('Import running')),
        (STATE_IMPORT_FINISHED, _('Import finished')),
        (STATE_IMPORT_FAILED, _('Import failed')),
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
    
    def append_to_report(self, text, report_class="info"):
        """ Adds a report text to the current report
            @param report_class: a str class. can be "error", "warning", "info" (default) or custom  """
        self.import_report_html += self.make_report_item(text, report_class).to_string()
    
    def make_user_report_container(self, report_items=None, report_class="info"):
        """ Makes a user report container item that can contain any number of report_items.
            Will add symbol markers of any of the contained items' error classes
            @param report_items: None or a list """
        report_items = report_items or []
        item_classes = list(set([item.report_class for item in report_items]))
        report_item_str = "".join([item.to_string() for item in report_items])
        return f'<div class="user-report {report_class}"><h3>TODO: Make accordion and add symbols for classes:{item_classes}</hh3>{report_item_str}</div>'
    
    def make_report_item(self, text, report_class="info"):
        """ Makes a report item.
            @param report_class: a str class. can be "error", "warning", "info" (default) or custom """
        return CosinnusUserImportReportItems(text, report_class)
    
    def clear_report(self):
        self.import_report_html = ""
    
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


class CosinnusUserImportProcessorBase(object):
    
    # lower case list of all column names known and used for the import
    KNOWN_CSV_IMPORT_COLUMNS_HEADERS = [
        'email',
        'first_name',
        'last_name',
    ]
    # required column headers to be present in the CSV data.
    # note: this does not mean the row data for this column is required, only the column should exist
    REQUIRED_CSV_IMPORT_COLUMN_HEADERS = KNOWN_CSV_IMPORT_COLUMNS_HEADERS
    # row data for each csv entry that need to not be empty in order for the import of that row to be accepted
    REQUIRED_ITEM_COLUMNS_FOR_IMPORT = [
        'email',
        'first_name',
    ]
    
    def do_import(self, user_import_item, dry_run=True, threaded=True):
        """ Does a threaded user import, either as a dry-run or real one.
            Will update the import object's state when done or failed.
            @property user_import_item: class `CosinnusUserImport` containing import_data """
        if dry_run:
            user_import_item.state = CosinnusUserImport.STATE_DRY_RUN_RUNNING
        else:
            user_import_item.state = CosinnusUserImport.STATE_IMPORT_RUNNING
        user_import_item.save()
        # start import
        my_self = self
        if threaded:
            class CosinnusUserImportProcessThread(Thread):
                def run(self):
                    my_self._start_import(user_import_item, dry_run=dry_run)
            CosinnusUserImportProcessThread().start()
        else:
            my_self._start_import(user_import_item, dry_run=dry_run)
    
    def _start_import(self, user_import_item, dry_run=True):
        """ Baseline implementation for a very simple user import  """
        try:
            for 
        except Exception as e:
            # if this outside exception happens, the import will be declared as "no data has been imported" and the errors will be shown
            logger.error(f'User Import: Critical failure during import (dry-run: {dry_run})', extra={'exception': e})
            if settings.DEBUG:
                raise e
            if dry_run:
                user_import_item.state = CosinnusUserImport.STATE_DRY_RUN_FINISHED_INVALID
            else:
                user_import_item.state = CosinnusUserImport.STATE_IMPORT_FAILED
            # prepend the error message
            user_import_item.import_report_html = user_import_item.make_report_item(
                _("An unexpected system error has occured while processing the data. This should not have happened. Please contact the support!"), 
                "error"
                ).to_string() + user_import_item.import_report_html
            user_import_item.save()
        

# allow dropin of labels class
CosinnusUserImportProcessor = CosinnusUserImportProcessorBase
if getattr(settings, 'COSINNUS_USER_IMPORT_PROCESSOR_CLASS_DROPIN', None):
    CosinnusUserImportProcessor = resolve_class(settings.COSINNUS_USER_IMPORT_PROCESSOR_CLASS_DROPIN)


