# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from django.http.response import Http404
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from cosinnus.views.mixins.tagged import HierarchyTreeMixin
from django.utils.encoding import force_text


class HierarchicalListCreateViewMixin(HierarchyTreeMixin):
    """ Hybrid view for hierarchic items.
        If allow_deep_hierarchy==True: Allows creation of folders inside other folders,
        else only allows creating them on the root level.
     """
    allow_deep_hierarchy = True
    
    def get_context_data(self, *args, **kwargs):
        # on form invalids, we need to retrieve the objects
        if not hasattr(self, 'object_list'):
            self.object_list = super(HierarchicalListCreateViewMixin, self).get_queryset()
        
        context = super(HierarchicalListCreateViewMixin, self).get_context_data(**kwargs)
        path = None
        slug = self.kwargs.pop('slug', None)
        if slug:
            try:
                path = self.object_list.get(slug=slug).path
            except self.model.DoesNotExist:
                raise Http404()
        root = path or '/'
        # assemble container and current hierarchy objects.
        # recursive must be =True, or we don't know how the size of a folder
        root_folder_node = self.get_tree(self.object_list, '/', include_containers=True, include_leaves=True, recursive=True)
        """ traverse tree and find the folder node which points to the given root """
        current_folder_node = root_folder_node
        for subfolder_name in root.split('/')[1:-1]:
            for find_folder in current_folder_node['containers']:
                if find_folder['path'].split('/')[-2] == subfolder_name:
                    current_folder_node = find_folder
        
        # we always show the folders from root if we only have 1 hierarchy level
        if self.allow_deep_hierarchy:
            folders = current_folder_node['containers']
        else:
            folders = root_folder_node['containers']
            
        objects = current_folder_node['objects']
        current_folder = current_folder_node['container_object']
        if current_folder is None:
            # insert logic for "this folder doesn't exist" here
            pass
        
        
        """ Collect a JSON list of all folders for this group
            Format: [{ "id" : "slug1", "parent" : "#", "text" : "Simple root node" }, 
                    { "id" : "slug2", "parent" : "slug1", "text" : "Child 1" },] """
        # TODO: this needs optimization (caching, or fold the DB call into the main folder-get call)
        all_folders = self.model.objects.filter(group=self.group, is_container=True)
        folders_only = self.get_tree(all_folders, '/', include_containers=True, include_leaves=False, recursive=True)
        all_folder_json = []
        if folders_only and folders_only.get('container_object', None):
            print folders_only
            def collect_folders(from_folder, folder_id='#'):
                cur_id = from_folder['container_object'].slug
                all_folder_json.append( {'id': cur_id, 'parent': folder_id, 'a_attr': {'target_folder':from_folder['container_object'].id}, 'text': escape(from_folder['name'] or force_text(_('<Root folder>')))} )
                for lower_folder in from_folder['containers']:
                    collect_folders(lower_folder, cur_id)
            collect_folders(folders_only)
        
        context.update({
            'current_folder': current_folder, 
            'object_list': objects, 
            'objects': objects, 
            'folders': folders,
            'is_deep_hierarchy': self.allow_deep_hierarchy,
            'all_folder_json': mark_safe(json.dumps(all_folder_json)),
        })
        return context
    

