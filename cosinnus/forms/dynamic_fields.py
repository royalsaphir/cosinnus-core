from cosinnus.dynamic_fields.dynamic_formfields import DynamicFieldFormFieldGenerator
from django import forms
from cosinnus.dynamic_fields.quick_import import BOELL_USERPROFILE_EXTRA_FIELDS
from cosinnus.dynamic_fields.dynamic_fields import DYNAMIC_FIELD_TYPE_ADMIN_DEFINED_CHOICES_TEXT


def get_dynamic_admin_field_namess():
    """ get all fields with type of DYNAMIC_FIELD_TYPE_ADMIN_DEFINED_CHOICES_TEXT """
    field_list = []

    for field_name, field in BOELL_USERPROFILE_EXTRA_FIELDS.items():
        if field.type == DYNAMIC_FIELD_TYPE_ADMIN_DEFINED_CHOICES_TEXT:
            field_list.append(field_name)

    return field_list


class DynamicFieldFormGenerator:
    def __init__(self, cosinnus_portal, *args, **kwargs):

        self._cosinnus_portal = cosinnus_portal
        self._forms = []

        self.saved = False

        for field_name in get_dynamic_admin_field_namess():
            # if 'data' in kwargs:
            #     # piping the request.POST to the right forms
            #     if
            form = DynamicFieldForm(self._cosinnus_portal, field_name, prefix=field_name, *args, **kwargs)
            self._forms.append(form)

    def try_save(self):
        for form in self._forms:
            if form.is_valid():
                form.save()
                self.saved = True

    def get_forms(self):
        return self._forms


class DynamicFieldForm(forms.Form):
    options = forms.CharField(max_length=1000)
    option_name = forms.CharField(widget=forms.HiddenInput)

    def clean_options(self):
        options = self.cleaned_data['options']
        option_list = []

        for option in options.split(","):
            # removing whitespaces from options
            option_list.append(option.strip())

        return option_list

    @property
    def id(self):
        return self._dynamic_field_name

    def save(self):
        self._cosinnus_portal.dynamic_field_choices[self._dynamic_field_name] = self.cleaned_data['options']
        self._cosinnus_portal.save()

    def __init__(self, cosinnus_portal, dynamic_field_name, *args, **kwargs):
        super(DynamicFieldForm, self).__init__(*args, **kwargs)

        self._dynamic_field_name = dynamic_field_name
        self._cosinnus_portal = cosinnus_portal
        self._field_choices = cosinnus_portal.dynamic_field_choices.get(dynamic_field_name, [])

        self.fields['options'].initial = ", ".join(self._field_choices)
        self.fields['option_name'].initial = ", ".join(self._dynamic_field_name)

    def get_cosinnus_dynamic_field(self, field_name):
        field = BOELL_USERPROFILE_EXTRA_FIELDS.get(field_name, "")
        if not field and not getattr(field, 'type', None) == DYNAMIC_FIELD_TYPE_ADMIN_DEFINED_CHOICES_TEXT:
            raise AttributeError(
                "%s is not a defined field in BOELL_USERPROFILE_EXTRA_FIELDS or nto type of "
                "DYNAMIC_FIELD_TYPE_ADMIN_DEFINED_CHOICES_TEXT"
            )
        return field