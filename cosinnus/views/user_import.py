# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.views.generic.edit import CreateView, FormView, UpdateView
from django.views.generic.list import ListView
from cosinnus.utils.permissions import check_user_superuser
from django.core.exceptions import PermissionDenied
from django.views.generic.base import TemplateView, View
from cosinnus.forms.administration import (UserWelcomeEmailForm,
NewsletterForManagedTagsForm, UserAdminForm)
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.newsletter import Newsletter
from django.urls.base import reverse
from cosinnus.views.user import _send_user_welcome_email_if_enabled
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import get_user_model

from cosinnus.views.profile import UserProfileUpdateView
from cosinnus.templatetags.cosinnus_tags import textfield
from cosinnus.utils.permissions import check_user_can_receive_emails
from cosinnus.utils.html import render_html_with_variables
from cosinnus.core.mail import send_html_mail_threaded
from cosinnus.models.group import CosinnusGroup
from cosinnus.models.managed_tags import CosinnusManagedTagAssignment
from cosinnus.views.user import email_first_login_token_to_user
from cosinnus.models.user_import import CosinnusUserImport
from cosinnus.views.mixins.group import RequireSuperuserMixin
from cosinnus.conf import settings

from django.db.models import Q
import logging
from sphinx.ext.autodoc.importer import import_object
from cosinnus.forms.user_import import CosinusUserImportCSVForm
from django.views.generic.detail import DetailView

logger = logging.getLogger('cosinnus')


class ArchivedCosinnusUserImportListView(RequireSuperuserMixin, ListView):
    
    model = CosinnusUserImport
    template_name = 'cosinnus/user_import/user_import_archived_list.html'

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(state=CosinnusUserImport.STATE_ARCHIVED)

archived_user_import_list_view = ArchivedCosinnusUserImportListView.as_view()


class ArchivedCosinnusUserImportDetailView(RequireSuperuserMixin, DetailView):
    
    model = CosinnusUserImport
    template_name = 'cosinnus/user_import/user_import_archived_detail.html'

archived_user_import_detail_view = ArchivedCosinnusUserImportDetailView.as_view()



class CosinnusUserImportView(RequireSuperuserMixin, TemplateView):
    
    http_method_names = ['get', 'post']
    template_name = 'cosinnus/user_import/user_import_form.html'
    redirect_view = reverse_lazy('cosinnus:administration-user-import')
    
    def get_current_import_object(self):
        self.import_object = None
        objects = CosinnusUserImport.objects.exclude(state=CosinnusUserImport.STATE_ARCHIVED)
        if objects.count() > 0:
            if objects.count() > 1:
                logger.warn('CosinnusUserImport: Accessed the import form with more than 1 import object of non-archived state present!')
                if settings.DEBUG:
                    raise Exception('Too many Import objects!')
            self.import_object = objects[0]
        return self.import_object
    
    def redirect_with_error(self, message=None):
        message = message or _('This action is not allowed right now')
        messages.error(self.request, message)
        return redirect(self.redirect_view)
    
    def set_form_view(self):
        self.form_view = None
        if not self.import_object:
            self.form_view = 'upload'
        else:
            if self.import_object.state  == CosinnusUserImport.STATE_DRY_RUN_RUNNING:
                self.form_view = 'dry-run-running'
            if self.import_object.state  == CosinnusUserImport.STATE_IMPORT_RUNNING:
                self.form_view = 'import-running'
            elif self.import_object.state == CosinnusUserImport.STATE_DRY_RUN_FINISHED_INVALID:
                self.form_view = 'invalid'
            elif self.import_object.state == CosinnusUserImport.STATE_DRY_RUN_FINISHED_VALID:
                self.form_view = 'import-ready'
            elif self.import_object.state == CosinnusUserImport.STATE_IMPORT_FINISHED:
                self.form_view = 'finished'
    
    def get(self, request, *args, **kwargs):
        self.get_current_import_object()
        self.set_form_view()
        return super(CosinnusUserImportView, self).get(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        self.get_current_import_object()
        self.set_form_view()
        self.action = self.request.POST.get('action', None)
        print(f'>>>> FORM ACTION: {self.action}')
        #csv = self.request.POST.get()
        # do stuff
        
        # disallowed states
        if self.import_object and self.import_object.state in \
                [CosinnusUserImport.STATE_DRY_RUN_RUNNING, CosinnusUserImport.STATE_IMPORT_RUNNING]:
            return self.redirect_with_error(_('Another import is currently running!'))
        
        if self.action == 'upload':
            # POST upload, can only do this when no current import exists
            if self.import_object:
                return self.redirect_with_error()
            upload_response = self.do_csv_upload()
            if upload_response:
                return upload_response
        elif self.action == 'import':
            # POST import, requires a valid dry run import object to exist
            if not self.import_object or not self.import_object.state == CosinnusUserImport.STATE_DRY_RUN_FINISHED_VALID:
                return self.redirect_with_error(_('No validated CSV upload found to start the import from!'))
            self.do_start_import_from_dryrun(self.import_object)
        elif self.action == 'archive':
            if not self.import_object or not self.import_object.state == CosinnusUserImport.STATE_IMPORT_FINISHED:
                return self.redirect_with_error()
            self.do_archive_import(self.import_object)
            return self.import_object.get_absolute_url()
        elif self.action == 'scrap':
            if not self.import_object or self.import_object.state in \
                    [CosinnusUserImport.STATE_DRY_RUN_FINISHED_INVALID, CosinnusUserImport.STATE_DRY_RUN_FINISHED_VALID]:
                return self.redirect_with_error()
            self.import_object.delete()
        else:
            return self.redirect_with_error(_('Unknown POST action!'))
        return redirect(self.redirect_view)
    
    def do_csv_upload(self):
        """ Returns a HTTPResponse if errrors, None otherwise """
        # parse csv in form
        form = CosinusUserImportCSVForm(files=self.request.FILES)
        setattr(self, 'form', form)
        if form.is_valid():
            print(f'>>> form valid!')
            csv_data = form.cleaned_data.get('csv')
            report_html = ''
            ignored_columns = csv_data['ignored_columns']
            if ignored_columns:
                report_html += f'<div class="warning">{_("The following columns were not recognized and were ignoried")}: {"".join(ignored_columns)}</div>'
            
            CosinnusUserImport.objects.create(
                creator=self.request.user,
                state=CosinnusUserImport.STATE_DRY_RUN_RUNNING,
                import_data=csv_data['data_dict_list'],
                import_report_html=report_html
            )
            # TODO: IMPORTER.start-dry-run threaded
            messages.success(self.request, _('The uploaded CSV is being validated.'))
        else:
            print(f'>>> formerorrs {self.form.errors}')
            return self.render_to_response(self.get_context_data())
            
            
    def do_start_import_from_dryrun(self, import_object):
        # do a non-dry-run import from the object
        import_object.state = CosinnusUserImport.STATE_IMPORT_RUNNING
        import_object.save()
        # TODO: IMPORTER.start-real-run threaded
        messages.success(self.request, _('The import was started.'))
    
    def do_archive_import(self, import_object):
        import_object.state = CosinnusUserImport.STATE_ARCHIVED
        import_object.save()
        messages.success(self.request, _('The import was successfully archived.'))
    
    def get_context_data(self, **kwargs):
        context = super(CosinnusUserImportView, self).get_context_data(**kwargs)
        context.update({
            'object': self.import_object,
            'form_view': self.form_view,
            'required_columns': 'TODO: required_columns',
            'form': getattr(self, 'form', CosinusUserImportCSVForm())
        })
        print(f'> CTXformerr {context["form"].errors}')
        return context

user_import_view = CosinnusUserImportView.as_view()

