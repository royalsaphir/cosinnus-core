# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
from collections import OrderedDict
import logging

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
import six

from django.core.cache import cache
from cosinnus.conf import settings
from cosinnus.utils.files import get_managed_tag_image_filename, image_thumbnail, \
    image_thumbnail_url
from cosinnus.utils.functions import clean_single_line_text, sort_key_strcoll_attr,\
    resolve_class
from cosinnus.utils.urls import get_domain_for_portal
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.validators import MaxLengthValidator


logger = logging.getLogger('cosinnus')


CosinnusPortal = None


class CosinnusManagedTagLabels(object):
    
    FA_ICON = 'fa-company'
    
    ASSIGNMENT_VERBOSE_NAME = _('Managed Tag Assignment')
    ASSIGNMENT_VERBOSE_NAME_PLURAL = _('Managed Tag Assignments')
    
    MANAGED_TAG_NAME = _('Managed Tag')
    MANAGED_TAG_NAME_PLURAL = _('Managed Tag')
    
    CREATE_MANAGED_TAG = _('Create Managed Tag')
    EDIT_MANAGED_TAG = _('Edit Managed Tag')
    DELETE_MANAGED_TAG = _('Delete Managed Tag')
    

# allow dropin of labels class
MANAGED_TAG_LABELS = CosinnusManagedTagLabels
if getattr(settings, 'COSINNUS_MANAGED_TAGS_LABEL_CLASS_DROPIN', None):
    MANAGED_TAG_LABELS = resolve_class(settings.COSINNUS_MANAGED_TAGS_LABEL_CLASS_DROPIN)


class CosinnusManagedTagManager(models.Manager):
    
    # main pk to object key
    _MANAGED_TAGS_PK_CACHE_KEY = 'cosinnus/core/portal/%d/managedtags/pks/%d' # portal_id, slug -> idea
    # (pk -> slug) dict
    _MANAGED_TAGS_SLUG_TO_PK_CACHE_KEY = 'cosinnus/core/portal/%d/managedtags/slugs' # portal_id -> {(slug, pk), ...} 
    
    def get_cached(self, slugs=None, pks=None, select_related_media_tag=True, portal_id=None):
        """
        Gets all ideas defined by either `slugs` or `pks`.

        `slugs` and `pks` may be a list or tuple of identifiers to use for
        request where the elements are of type string / unicode or int,
        respectively. You may provide a single string / unicode or int directly
        to query only one object.

        :returns: An instance or a list of instances of :class:`CosinnusGroup`.
        :raises: If a single object is defined a `CosinnusGroup.DoesNotExist`
            will be raised in case the requested object does not exist.
        """
        if portal_id is None:
            portal_id = CosinnusPortal.get_current().id
            
        # Check that at most one of slugs and pks is set
        assert not (slugs and pks)
        assert not (slugs or pks)
            
        if slugs is not None:
            if isinstance(slugs, six.string_types):
                # We request a single idea
                slugs = [slugs]
                
            # We request multiple ideas by slugs
            keys = [self._IDEAS_SLUG_CACHE_KEY % (portal_id, s) for s in slugs]
            ideas = cache.get_many(keys)
            missing = [key.split('/')[-1] for key in keys if key not in ideas]
            if missing:
                # we can only find ideas via this function that are in the same portal we run in
                query = self.get_queryset().filter(portal__id=portal_id, is_active=True, slug__in=missing)
                if select_related_media_tag:
                    query = query.select_related('media_tag')
                
                for idea in query:
                    ideas[self._IDEAS_SLUG_CACHE_KEY % (portal_id, idea.slug)] = idea
                cache.set_many(ideas, settings.COSINNUS_IDEA_CACHE_TIMEOUT)
            
            # sort by a good sorting function that acknowldges umlauts, etc, case insensitive
            idea_list = list(ideas.values())
            idea_list = sorted(idea_list, key=sort_key_strcoll_attr('name'))
            return idea_list
            
        elif pks is not None:
            if isinstance(pks, int):
                pks = [pks]
            else:
                # We request multiple ideas
                cached_pks = self.get_pks(portal_id=portal_id)
                slugs = [_f for _f in (cached_pks.get(pk, []) for pk in pks) if _f]
                if slugs:
                    return self.get_cached(slugs=slugs, portal_id=portal_id)
                return []  # We rely on the slug and id maps being up to date
        return []
    
    
    def get_pks(self, portal_id=None, force=True):
        """
        Gets the (pks -> slug) :class:`OrderedDict` from the cache or, if the can has not been filled,
        gets the pks and slugs from the database and fills the cache.
        
        @param force: if True, forces a rebuild of the pk and slug cache for this group type
        :returns: A :class:`OrderedDict` with a `pk => slug` mapping of all
            groups
        """
        if portal_id is None:
            portal_id = CosinnusPortal.get_current().id
            
        pks = cache.get(self._IDEAS_PK_TO_SLUG_CACHE_KEY % (portal_id))
        if force or pks is None:
            # we can only find groups via this function that are in the same portal we run in
            pks = OrderedDict(self.filter(portal__id=portal_id, is_active=True).values_list('id', 'slug').all())
            cache.set(self._IDEAS_PK_TO_SLUG_CACHE_KEY % (portal_id), pks,
                settings.COSINNUS_IDEA_CACHE_TIMEOUT)
        return pks

    
    def all_in_portal(self):
        """ Returns all groups within the current portal only """
        return self.active().filter(portal=CosinnusPortal.get_current())
    
    def public(self):
        """ Returns active, public Ideas """
        qs = self.active()
        return qs.filter(public=True)
    
    def active(self):
        """ Returns active Ideas """
        qs = self.get_queryset()
        return qs.filter(is_active=True)
    
    def get_by_shortid(self, shortid):
        """ Gets an idea from a string id in the form of `"%(portal)d.%(type)s.%(slug)s"`. 
            Returns None if not found. """
        portal, __, slug = shortid.split('.')
        portal = int(portal)
        try:
            qs = self.get_queryset().filter(portal_id=portal, slug=slug)
            return qs[0]
        except self.model.DoesNotExist:
            return None
        
    
class CosinnusManagedTagAssignment(models.Model):
    """ The assignment intermediate-Model for CosinnusManagedTag """
    
    managed_tag = models.ForeignKey('cosinnus.CosinnusManagedTag', related_name='assignments', on_delete=models.CASCADE)
    
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    target_object = GenericForeignKey('content_type', 'object_id')
    
    assigners = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='managed_tag_assignments', blank=True,
        help_text='A list of people who suggested making this assignment. Can be empty, and can beignored once `approved` is True.')
    approved = models.BooleanField(verbose_name=_('Approved'), default=False)
    last_modified = models.DateTimeField(verbose_name=_('Last modified'), editable=False, auto_now=True)

    class Meta(object):
        app_label = 'cosinnus'
        unique_together = (('managed_tag', 'content_type', 'object_id'),)
        verbose_name = MANAGED_TAG_LABELS.ASSIGNMENT_VERBOSE_NAME
        verbose_name_plural = MANAGED_TAG_LABELS.ASSIGNMENT_VERBOSE_NAME_PLURAL

    def __str__(self):
        return "<managed tag assignment: %(managed_tag)s, content_type: %(content_type)s, target_object_id: %(target_object_id)d>" % {
            'managed_tag': getattr(self, 'managed_tag', None),
            'content_type': getattr(self, 'content_type', None),
            'target_object_id': getattr(self, 'target_object_id', None),
        }


@python_2_unicode_compatible
class CosinnusManagedTag(models.Model):
    
    # don't worry, the default Portal with id 1 is created in a datamigration
    # there was no other way to generate completely runnable migrations 
    # (with a get_default function, or any other way)
    portal = models.ForeignKey('cosinnus.CosinnusPortal', verbose_name=_('Portal'), related_name='managed_tags', 
        null=False, blank=False, default=1, on_delete=models.CASCADE) # port_id 1 is created in a datamigration!
    
    name = models.CharField(_('Name'), max_length=250) 
    slug = models.SlugField(_('Slug'), 
        help_text=_('Be extremely careful when changing this slug manually! There can be many side-effects (redirects breaking e.g.)!'), 
        max_length=50)
    
    description = models.TextField(verbose_name=_('Short Description'), blank=True)
    
    image = models.ImageField(_("Image"), 
        null=True, blank=True,
        upload_to=get_managed_tag_image_filename,
        max_length=250)
    
    color = models.CharField(_('Color'),
         max_length=10, validators=[MaxLengthValidator(7)],
         help_text=_('Optional color code (css hex value, with or without "#")'),
         blank=True, null=True)
    
    paired_group = models.ForeignKey(settings.COSINNUS_GROUP_OBJECT_MODEL, 
        verbose_name=_('Paired Group'),
        blank=True, null=True, related_name='paired_managed_tag',
        on_delete=models.SET_NULL,
        help_text='A paired group will automatically be joined by all users assigned to this.')
    
    created = models.DateTimeField(verbose_name=_('Created'), editable=False, auto_now_add=True)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('Creator'), on_delete=models.CASCADE,
        null=True, blank=True, related_name='+')
    last_modified = models.DateTimeField( verbose_name=_('Last modified'), editable=False, auto_now=True)
    
    
    #objects = CosinnusManagedTagManager()
    
    class Meta(object):
        ordering = ('name',)
        verbose_name = MANAGED_TAG_LABELS.MANAGED_TAG_NAME
        verbose_name_plural = MANAGED_TAG_LABELS.MANAGED_TAG_NAME_PLURAL
        unique_together = (('slug', 'portal'), )

    def __str__(self):
        return '%s (Portal %d)' % (self.name, self.portal_id)
    
    def get_icon(self):
        """ Returns the font-awesome icon specific to this object type """
        return MANAGED_TAG_LABELS.FA_ICON
    
    def save(self, *args, **kwargs):
        created = bool(self.pk is None)
        slugs = [self.slug] if self.slug else []
        self.name = clean_single_line_text(self.name)
        
        current_portal = self.portal or CosinnusPortal.get_current()
        
        if not self.slug:
            raise ValidationError(_('Slug must not be empty.'))
        slugs.append(self.slug)
        
        # set portal to current
        if created and not self.portal:
            self.portal = current_portal
            
        super(CosinnusManagedTag, self).save(*args, **kwargs)
        
        # todo: caching
        # self._clear_cache(slugs=slugs)
        # force rebuild the pk --> slug cache. otherwise when we query that, this group might not be in it
        # self.__class__.objects.get_pks(force=True)
        
        self._portal_id = self.portal_id
        self._slug = self.slug
    
    def delete(self, *args, **kwargs):
        # todo: caching
        #self._clear_cache(slug=self.slug)
        super(CosinnusManagedTag, self).delete(*args, **kwargs)
        
    @classmethod
    def _clear_cache(self, slug=None, slugs=None):
        # todo: caching
        slugs = set([s for s in slugs]) if slugs else set()
        if slug: slugs.add(slug)
        keys = [
            self.objects._IDEAS_PK_TO_SLUG_CACHE_KEY % (CosinnusPortal.get_current().id),
        ]
        if slugs:
            keys.extend([self.objects._IDEAS_SLUG_CACHE_KEY % (CosinnusPortal.get_current().id, s) for s in slugs])
        cache.delete_many(keys)
        
    def clear_cache(self):
        # todo: caching
        self._clear_cache(slug=self.slug)
        
    @property
    def image_url(self):
        return self.image.url if self.image else None
    
    def get_image_thumbnail(self, size=(500, 275)):
        return image_thumbnail(self.image, size)

    def get_image_thumbnail_url(self, size=(500, 275)):
        return image_thumbnail_url(self.image, size)
    
    def get_absolute_url(self):
        # todo
        return get_domain_for_portal(self.portal) + '???tag/' + self.slug
    
