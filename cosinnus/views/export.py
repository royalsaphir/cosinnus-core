# -*- coding: utf-8 -*-
from __future__ import unicode_literals

"""
Export views to be used by cosinnus apps
"""

import json

from django.http import HttpResponse
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from django.views.generic import View

from cosinnus.views.mixins.group import RequireAdminMixin


class JSONExportView(RequireAdminMixin, View):
    """
    View to return a JSON document which contains an app's model data on
    GET requests. Requires the user to have admin rights (on the current group)
    """

    #: list of field names to be exported; each field needs to be representable as string
    fields = []

    #: model to get data from; required to be set by subclassing view
    model = None

    #: prefix of the name of the returned file, usually the app name
    file_prefix = 'cosinnus'

    def __init__(self, *args, **kwargs):
        if not self.model:
            raise AttributeError(_('No model given to export data from.'))
        super(JSONExportView, self).__init__(*args, **kwargs)

    def get_json(self):
        data = {
            'group': self.group.name,
            'fields': ['id', 'title'] + self.fields,
            'rows': [],
        }
        for obj in self.model.objects.filter(group=self.group).order_by('pk'):
            row = [str(obj.pk), obj.title]
            for field in self.fields:
                row.append(str(getattr(obj, field, '')))
            data['rows'].append(row)
        return json.dumps(data)

    def get(self, request, *args, **kwargs):
        json_data = self.get_json()
        response = HttpResponse(json_data, content_type='application/json')
        filename = '%s.%s.%s.json' % (
            self.file_prefix, self.group.slug, now().strftime('%Y%m%d%H%M%S'))
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename

        return response
