# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from cosinnus.models.group import  CosinnusPortal

from wagtail.wagtailcore.models import Page
from wagtail.wagtailcore.fields import RichTextField, RichTextArea
from wagtail.wagtailadmin.edit_handlers import FieldPanel
from wagtail.wagtailsearch import index
from wagtail.wagtailadmin.edit_handlers import ObjectList
from wagtail.wagtailadmin.views.pages import PAGE_EDIT_HANDLERS

from wagtail_modeltranslation.models import TranslationMixin

from django.shortcuts import redirect
from cosinnus.utils.urls import get_non_cms_root_url
from wagtail.wagtailcore.rich_text import DbWhitelister



class BetterDbWhitelister(DbWhitelister):
    """ Prevents <div> tags from being replaced by <p> """
    
    @classmethod
    def clean_tag_node(cls, doc, tag):
        if not 'data-embedtype' in tag.attrs and tag.name == 'div':
            super(DbWhitelister, cls).clean_tag_node(doc, tag) # this gets around having the 'div' tag replaced
        else:
            super(BetterDbWhitelister, cls).clean_tag_node(doc, tag)
            

class BetterRichTextArea(RichTextArea):
    """ Enables using a custom DbWhitelister """
    
    def value_from_datadict(self, data, files, name):
        original_value = super(RichTextArea, self).value_from_datadict(data, files, name)
        if original_value is None:
            return None
        return BetterDbWhitelister.clean(original_value)


class BetterRichTextField(RichTextField):
    """ Enables using a custom DbWhitelister """
    
    def formfield(self, **kwargs):
        defaults = {'widget': BetterRichTextArea}
        defaults.update(kwargs)
        return super(RichTextField, self).formfield(**defaults) # super on RichTextField, not self.__class__!


class SplitMultiLangTabsMixin(object):
    """ This mixin detects multi-language fields and splits them into seperate tabs per language """
    
    def _split_i18n_wagtail_translated_panels(self, content_panels):
        """ For use with wagtail and wagtail-modeltranslation. This will encapsulate all translatable
            Page content fields in a seperate tab for each language in the wagtail admin.
         """
        object_lists = []
        for (lang, _lang_label) in getattr(settings, 'MODELTRANSLATION_LANGUAGES', getattr(settings, 'LANGUAGES', [])):
            i18n_content_panels = []
            for field_panel in content_panels:
                if field_panel.field_name.endswith(lang):
                    mod = type(field_panel)(field_panel.field_name, classname=field_panel.classname)
                    i18n_content_panels.append( mod )
            object_lists.append(ObjectList(i18n_content_panels, heading=_('Content') + ' (%(language)s)' % {'language': lang}))
        return object_lists 
    
    def __init__(self, *args, **kwargs):
        super(SplitMultiLangTabsMixin, self).__init__(*args, **kwargs)
        if self.__class__ in PAGE_EDIT_HANDLERS and not getattr(PAGE_EDIT_HANDLERS[self.__class__], '_MULTILANG_TABS_PATCHED', False):
            handler = PAGE_EDIT_HANDLERS[self.__class__]
            tabs = [tab_handler.bind_to_model(self.__class__) for tab_handler in self._split_i18n_wagtail_translated_panels(self.content_panels)]
            handler.children = tabs + handler.children[1:]
            handler._MULTILANG_TABS_PATCHED = True


class PortalRootPage(SplitMultiLangTabsMixin, TranslationMixin, Page):
    
    class Meta:
        verbose_name = _('Portal Root Page')
        
    # this template should never be visible, but if it is, the user will see an explanation
    template = 'cosinnus/wagtail/portal_root_page.html'
        
    parent_page_types = ['wagtailcore.Page', ]
    
    portal = models.ForeignKey(CosinnusPortal, verbose_name=_('Assigned Portal'), 
        related_name='wagtail_root_pages', 
        help_text='Only portal admins of the assigned portal can see wagtail pages below this one.',
        null=True, blank=True, on_delete=models.SET_NULL)
    
    footer = BetterRichTextField(verbose_name=_('Footer'), blank=True,
        help_text=_('Will be displayed as a footer on EVERY page on this website (not only dashboard pages!)'))
    
    
    # Editor panels configuration
    content_panels = Page.content_panels + [
        FieldPanel('footer', classname="full"),
    ]
    
    # Editor panels configuration
    settings_panels = Page.settings_panels + [
        FieldPanel('portal'),
    ]
    
    translation_fields = (
        'footer',
    )


class BaseDashboardPage(SplitMultiLangTabsMixin, TranslationMixin, Page):
    
    class Meta:
        abstract = True
    
    # settings fields
    show_register_button = models.BooleanField(_('Show Register Button'), default=True)
    redirect_if_logged_in = models.BooleanField(_('Redirect Logged in Users'),
        help_text=_('If active, this page will only be visible to non-logged-in users. All others will be redirected to the activities page.'),
        default=False)
    
    # Database fields
    banner_left = BetterRichTextField(verbose_name=_('Left banner (top)'), blank=True)
    banner_right = BetterRichTextField(verbose_name=_('Right banner (top)'), blank=True)
    
    header = BetterRichTextField(verbose_name=_('Header'), blank=True)
    
    footer_left = BetterRichTextField(verbose_name=_('Left footer'), blank=True)
    footer_right = BetterRichTextField(verbose_name=_('Right footer'), blank=True)
    
    translation_fields = (
        'title',
        'banner_left',
        'banner_right',
        'header',
        'footer_left',
        'footer_right',
    )
    
    # Search index configuraiton
    search_fields = Page.search_fields + (
        index.SearchField('banner_left'),
        index.SearchField('banner_right'),
        index.SearchField('header'),
        index.SearchField('footer_left'),
        index.SearchField('footer_right'),
    )

    # Editor panels configuration
    content_panels = Page.content_panels + [
        FieldPanel('banner_left', classname="full"),
        FieldPanel('banner_right', classname="full"),
        FieldPanel('header', classname="full"),
        FieldPanel('footer_left', classname="full"),
        FieldPanel('footer_right', classname="full"),
    ]
    
    # Editor panels configuration
    settings_panels = Page.settings_panels + [
        FieldPanel('show_register_button'),
        FieldPanel('redirect_if_logged_in'),
    ]
    
    def serve(self, request):
        """ If the redirect flag is set, and the user is logged in, redirect to streams, otherwise, show CMS page """
        if request.user.is_authenticated() and self.redirect_if_logged_in and not request.GET.get('preview', False):
            return redirect(get_non_cms_root_url())
        return super(BaseDashboardPage, self).serve(request)


class DashboardSingleColumnPage(BaseDashboardPage):
    
    class Meta:
        verbose_name = _('1-Column Dashboard Page')
    
    content1 = BetterRichTextField(verbose_name=_('Content'), blank=True)

    # Search index configuraiton
    search_fields = BaseDashboardPage.search_fields + (
        index.SearchField('content1'),
    )

    # Editor panels configuration
    content_panels = BaseDashboardPage.content_panels + [
        FieldPanel('content1', classname="full"),
    ]
    
    template = 'cosinnus/wagtail/dashboard_single_column_page.html'
    
    translation_fields = BaseDashboardPage.translation_fields + (
        'content1',
    )
    
    

class DashboardDoubleColumnPage(BaseDashboardPage):
    
    class Meta:
        verbose_name = _('2-Column Dashboard Page')
    
    content1 = BetterRichTextField(verbose_name=_('Content (left column)'), blank=True)
    content2 = BetterRichTextField(verbose_name=_('Content (right column)'), blank=True)

    # Search index configuraiton
    search_fields = BaseDashboardPage.search_fields + (
        index.SearchField('content1'),
        index.SearchField('content2'),
    )

    # Editor panels configuration
    content_panels = BaseDashboardPage.content_panels + [
        FieldPanel('content1', classname="full"),
        FieldPanel('content2', classname="full"),
    ]
    
    template = 'cosinnus/wagtail/dashboard_double_column_page.html'
    
    translation_fields = BaseDashboardPage.translation_fields + (
        'content1',
        'content2',
    )
    
    
class DashboardTripleColumnPage(BaseDashboardPage):
    
    class Meta:
        verbose_name = _('3-Column Dashboard Page')
    
    content1 = BetterRichTextField(verbose_name=_('Content (left column)'), blank=True)
    content2 = BetterRichTextField(verbose_name=_('Content (center column)'), blank=True)
    content3 = BetterRichTextField(verbose_name=_('Content (right column)'), blank=True)
    
    # Search index configuraiton
    search_fields = BaseDashboardPage.search_fields + (
        index.SearchField('content1'),
        index.SearchField('content2'),
        index.SearchField('content3'),
    )

    # Editor panels configuration
    content_panels = BaseDashboardPage.content_panels + [
        FieldPanel('content1', classname="full"),
        FieldPanel('content2', classname="full"),
        FieldPanel('content3', classname="full"),
    ]

    template = 'cosinnus/wagtail/dashboard_triple_column_page.html'
    
    translation_fields = BaseDashboardPage.translation_fields + (
        'content1',
        'content2',
        'content3',
    )
    
    
class BaseSimplePage(SplitMultiLangTabsMixin, TranslationMixin, Page):
    
    class Meta:
        abstract = True
    
    # Database fields
    content = BetterRichTextField(verbose_name=_('Content'), blank=True)
    
    # Search index configuraiton
    search_fields = Page.search_fields + (
        index.SearchField('content'),
    )

    # Editor panels configuration
    content_panels = Page.content_panels + [
        FieldPanel('content', classname="full"),
    ]
    
    translation_fields = (
        'content',
        'title',
    )
    
        
class SimpleOnePage(BaseSimplePage):
    
    class Meta:
        verbose_name = _('Simple One-Column Page')
    
    template = 'cosinnus/wagtail/simple_one_page.html'
    

class SimpleTwoPage(BaseSimplePage):
    
    class Meta:
        verbose_name = _('Simple Page with Left Navigation')
    
    # Database fields
    leftnav = BetterRichTextField(verbose_name=_('Left Sidebar'), blank=True)
    
    # Search index configuraiton
    search_fields = BaseSimplePage.search_fields + (
        index.SearchField('leftnav'),
    )

    # Editor panels configuration
    content_panels = BaseSimplePage.content_panels + [
        FieldPanel('leftnav', classname="full"),
    ]

    template = 'cosinnus/wagtail/simple_two_page.html'
    
    translation_fields = SimpleOnePage.translation_fields + (
        'leftnav',
    )