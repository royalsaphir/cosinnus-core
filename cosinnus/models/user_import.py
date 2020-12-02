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
from django.contrib.auth import get_user_model

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
    
    user_report_items = None
    
    class Meta(object):
        ordering = ('-last_modified',)
        verbose_name = _('Cosinnus User Import')
        verbose_name_plural = _('Cosinnus User Imports')

    def __init__(self, *args, **kwargs):
        self.user_report_items = []
        super(CosinnusUserImport, self).__init__(*args, **kwargs)

    def __str__(self):
        return f'<UserImport from {self.last_modified}>'
    
    def append_to_report(self, text, report_class="info"):
        """ Adds a report text to the current report
            @param report_class: a str class. can be "error", "warning", "info" (default) or custom  """
        self.import_report_html += CosinnusUserImportReportItems(text, report_class).to_string()
    
    def generate_and_append_user_report(self, header_text, report_class="info"):
        """ Makes a user report container item from all accrued `self.user_report_items`.
            Will add symbol markers of any of the contained items' error classes
            @param report_items: None or a list """
        item_classes = list(set([item.report_class for item in self.user_report_items]))
        report_item_str = "".join([item.to_string() for item in self.user_report_items])
        self.import_report_html += f'<div class="user-report {report_class}"><h1>{header_text}</h1><h3>TODO: Make accordion and add symbols for classes:{item_classes}</hh3>{report_item_str}</div>'
        self.clear_user_report_items()
    
    def add_user_report_item(self, text, report_class="info"):
        """ Makes a report item.
            @param report_class: a str class. can be "error", "warning", "info" (default) or custom """
        self.user_report_items.append(CosinnusUserImportReportItems(text, report_class))
        
    def clear_user_report_items(self):
        self.user_report_items = []
    
    def clear_report(self):
        self.import_report_html = ""
    
    def save(self, *args, **kwargs):
        # sanity check: if the to-be-saved state isn't STATE_ARCHIVED, make sure no other import exists that isn't archived
        if self.state != CosinnusUserImport.STATE_ARCHIVED:
            created = bool(self.pk is None)
            existing_imports = CosinnusUserImport.objects.exclude(state=CosinnusUserImport.STATE_ARCHIVED)
            if not created:
                existing_imports = existing_imports.exclude(id=self.id)
            if existing_imports.count() > 0:
                raise Exception('CosinnusUserImport: Could not save import object because state check failed: there is another import that is not archived.')
        super(CosinnusUserImport, self).save(*args, **kwargs)
        
    def get_absolute_url(self):
        return reverse('cosinnus:administration-archived-user-import-detail', kwargs={'pk': self.id})


class CosinnusUserImportProcessorBase(object):
    
    # a mapping of column header names to user/userprofile/user-media-tag field names
    # important: the keys are *ALWAYS* lower-case as the CSV importer will lower().strip() them!
    CSV_HEADERS_TO_FIELD_MAP = {
        'email': 'email',
        'firstname': 'first_name',
        'lastname':'last_name',
    }
    
    # lower case list of all column names known and used for the import
    KNOWN_CSV_IMPORT_COLUMNS_HEADERS = CSV_HEADERS_TO_FIELD_MAP.keys()
    # required column headers to be present in the CSV data.
    # note: this does not mean the row data for this column is required, only the column should exist
    REQUIRED_CSV_IMPORT_COLUMN_HEADERS = KNOWN_CSV_IMPORT_COLUMNS_HEADERS
    # field names for csv entry row data that need to not be empty in order for the import of that row to be accepted
    # these are the *FIELD NAMES*, not the CSV column headers! so this is from `CSV_HEADERS_TO_FIELD_MAP.values()`!
    REQUIRED_FIELDS_FOR_IMPORT = [
        'email',
        'first_name',
    ]
    # reverse map of CSV_HEADERS_TO_FIELD_MAP, initialized on init
    field_name_map = None 
    
    
    def __init__(self):
        # init the reverse map here in case the header map gets changed in the cls 
        self.field_name_map = dict([(val, key) for key, val in self.CSV_HEADERS_TO_FIELD_MAP.items()])
    
    def do_import(self, user_import_item, dry_run=True, threaded=True):
        """ Does a threaded user import, either as a dry-run or real one.
            Will update the import object's state when done or failed.
            @property user_import_item: class `CosinnusUserImport` containing import_data """
        if settings.DEBUG:
            threaded = False # never thread in dev
            
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
        import_failed_overall = False
        try:
            for item_data in user_import_item.import_data:
                # clear user item reports
                user_import_item.clear_user_report_items()
                # sanity check: all absolutely required fields must exist:
                missing_fields = [self.field_name_map[req_field] for req_field in self.REQUIRED_FIELDS_FOR_IMPORT if not item_data.get(self.field_name_map[req_field], None)]
                if missing_fields:
                    import_successful = False
                    user_import_item.add_user_report_item(
                            _('CSV row %(row_num)d was missing required data from columns: %(fields)s') % {'fields': ", ".join(missing_fields), 'row_num': item_data['ROW_NUM']},
                            report_class="error"
                        )
                else:
                    import_successful = self._do_single_user_import(item_data, user_import_item, dry_run=dry_run)
                    
                report_class = "info" if import_successful else "error"
                user_import_item.generate_and_append_user_report(self.get_user_report_title(item_data), report_class)
                
                # instantly fail a real import when a single user could not be imported. this should have been
                # caught by the dry-run validation (which wouldve disabled the real import), or hints at a serious
                # relational problem that should be looked into
                if not import_successful:
                    import_failed_overall = True
                    if not dry_run:
                        # prepend the error message
                        user_import_item.import_report_html = CosinnusUserImportReportItems(
                            _("Import for a user item has failed, cancelling the import process! TODO: has data been written?"), 
                            "error"
                            ).to_string() + user_import_item.import_report_html
                        break
                    
                
        except Exception as e:
            # if this outside exception happens, the import will be declared as "no data has been imported" and the errors will be shown
            logger.error(f'User Import: Critical failure during import (dry-run: {dry_run})', extra={'exception': e})
            import_failed_overall = True
            # prepend the error message
            user_import_item.import_report_html = CosinnusUserImportReportItems(
                _("An unexpected system error has occured while processing the data. This should not have happened. Please contact the support!"), 
                "error"
                ).to_string() + user_import_item.import_report_html
            if settings.DEBUG:
                if dry_run:
                    user_import_item.state = CosinnusUserImport.STATE_DRY_RUN_FINISHED_INVALID
                else:
                    user_import_item.state = CosinnusUserImport.STATE_IMPORT_FAILED
                user_import_item.save()
                raise e
            
        if import_failed_overall:
            if dry_run:
                user_import_item.state = CosinnusUserImport.STATE_DRY_RUN_FINISHED_INVALID
            else:
                user_import_item.state = CosinnusUserImport.STATE_IMPORT_FAILED
        else:
            if dry_run:
                user_import_item.state = CosinnusUserImport.STATE_DRY_RUN_FINISHED_VALID
            else:
                user_import_item.state = CosinnusUserImport.STATE_IMPORT_FINISHED 
        user_import_item.save()
            
    def _do_single_user_import(self, item_data, user_import_item, dry_run=True):
        """ Main import function for a single user data object.
            During this, user_item_reports should be accrued for the item
            @param item_data: A dict object containing keys corresponding to `KNOWN_CSV_IMPORT_COLUMNS_HEADERS` and the row data for one user
            @return: A django.auth.User object if successful, None if not """
        user = self._import_create_auth_user(item_data, user_import_item, dry_run=dry_run)
        if not user:
            return False
        return True
        
    
    def _import_create_auth_user(self, item_data, user_import_item, dry_run=True):
        """ Create a user object from import.
            @return: None if not successful, else a auth user object """
        # fields are in REQUIRED_FIELDS_FOR_IMPORT so we can assume they exist
        email = item_data.get(self.field_name_map['email']) 
        first_name = item_data.get(self.field_name_map['first_name']) 
        last_name = item_data.get(self.field_name_map['last_name'], None) 
        
        email_exists = get_user_model().objects.filter(email__iexact=email).exists()
        if email_exists:
            user_import_item.add_user_report_item(_('This email-address already has an existing user account in the system!'), report_class="error")
            return None
        user_kwargs = {
            'username': email,
            'email': email,
            'first_name': first_name,
        }
        if last_name:
            user_kwargs['last_name'] = last_name
        user = get_user_model()(**user_kwargs)
        
        if settings.DEBUG:
            # TODO: fix for real applications
            user.password = 'pwd123'
            
        if not dry_run:
            user.save()
            user.username = user.id
            user.save()
            
        del user_kwargs['username']
        user_import_item.add_user_report_item(str(_('New user account: ') + str(user_kwargs)), report_class="error")
        return user
    
    def get_user_report_title(self, item_data):
        return item_data.get('first_name', '<no-name>') + ' ' + item_data.get('email', '<no-email>') + ' csv-row: #' + str(item_data['ROW_NUM'])
        
        

# allow dropin of labels class
CosinnusUserImportProcessor = CosinnusUserImportProcessorBase
if getattr(settings, 'COSINNUS_USER_IMPORT_PROCESSOR_CLASS_DROPIN', None):
    CosinnusUserImportProcessor = resolve_class(settings.COSINNUS_USER_IMPORT_PROCESSOR_CLASS_DROPIN)


