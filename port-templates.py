#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
django-template-porting-util: Update Django template syntax from .9x to 1.0.

This program automates much of the process of moving your Django templates from
Django .9x to Django 1.0. It is safe to re-run this program on templates if,
for example, you are porting templates while the old templates are still in use
and subject to change. Just put any new templates in the template directory and
re-run. Remember that you can also point to a specific directory, or even a
specific template.

WARNING: This program irreversibly alters your templates! It is essential that
you use some form of version control or at least make backups of your files
before every use.

"""
# Note that __future__ imports must go at the top.
from __future__ import with_statement

__author__ = "Ben Spaulding"
__contributors__ = ["Daniel Lindsley",]
__copyright__ = "Copyright (c) 2008, Ben Spaulding. All rights reserved."
__description__ = "Update Django template syntax from .9x to 1.0."
__url__ = "http://github.com/benspaulding/django-template-porting-util"
__version__ = "0.9"

import os
import re
import sys
import yaml
import unittest
from pprint import PrettyPrinter
from optparse import OptionParser

try:
    from django.template import BLOCK_TAG_START, BLOCK_TAG_END
    from django.template import VARIABLE_TAG_START, VARIABLE_TAG_END
    from django.template import COMMENT_TAG_START, COMMENT_TAG_END
    DJANGO_SETTINGS_MODULE = os.environ['DJANGO_SETTINGS_MODULE']
except (ImportError, KeyError):
    print u"Cannot find Django. Did you setup your environment correctly? (Don’t forget to set the DJANGO_SETTINGS_MODULE environment variable.)"
    sys.exit()


class TemplateMonkey(object):

    def __init__(self):

        try:
            self.settings = __import__(options.settings)
            os.environ['DJANGO_SETTINGS_MODULE'] = options.settings
        except ImportError:
            print u"Cannot load settings module."
            sys.exit()

        self.printer = PrettyPrinter(indent=2)
        config = self.load_config()
        self.extensions = config['extensions']
        self.related_names = config['related_names']
        self.ignored_methods = config['ignored_methods']
        self.template_paths = config['template_paths']

        # Compile the regexen here for speed.
        self.extension_regex = re.compile('{%\s+(?P<tag>extends|include)\s+(\"|\')(?P<file_path>.*?)(\"|\')\s+%}')
        self.file_field_regex = re.compile('(?P<prepend_char>\.|\"|\')get_(?P<field>.*?)_(?P<method>url|size|file|width|height|filename)')
        self.rel_basic_regex = re.compile('(?P<prepend_char>\.|\"|\')get_(?P<field>.*?)(?P<following_char>\s|\.)')
        self.rel_count_regex = re.compile('(?P<prepend_char>\.|\"|\')get_(?P<field>.*?)_count')
        self.rel_list_regex = re.compile('(?P<prepend_char>\.|\"|\')get_(?P<field>.*?)_list')


    def port_templates(self):
        """Run requested methods on the specified templates."""

        if not options.add_extension and \
           not options.update_file_fields and \
           not options.update_relations:
            print u"This monkey won’t do anything unless you tell it to — see available options by running “port-templates.py --help”"
            sys.exit()

        for template_path in self.template_paths:
            # Using “with” statements with file objcts is good practice, per
            # http://docs.python.org/tutorial/inputoutput.html
            # Note that “with” statements have to be enabled in Python 2.5. See
            # http://docs.python.org/whatsnew/2.5.html#pep-343-the-with-statement
            with open(template_path, 'r+') as template:
                # Stow the original.
                original_template = template
                ported_template = ''

                for line in template:
                    # Now call each method on every line of the template, as needed.
                    if options.add_extension:
                        line = self.add_extension(line)
                    if options.update_file_fields:
                        line = self.update_file_fields(line)
                    if options.update_relations:
                        line = self.update_relations(line)

                    ported_template += line

                if not options.dry_run:
                    ported_template_file = open(template_path, 'w')
                    ported_template_file.write(ported_template)
                    ported_template_file.close()
                else:
                    from difflib import unified_diff
                    print u"Diff for ‘%s’" % template_path
                    print u"".join(unified_diff(original_template, ported_template))
                    print


    def load_config(self):
        """
        Create configuration dictionary from various sources.

        Loads the specified YAML configuration file and adds all
        methods found on any model in settings.INSTALLED_APPS to
        the ignored_methods list, and then removes any methods
        in force_update from ignored_methods.

        """
        from django.db import models

        # Q: Should I be using a try/except block or while?
        # Q: If with is used, how do I handle exceptions in a with statement?
        # Q: What if config_file is moved/altered while after being opened,
        #    and before being closed? Anything?
        # try:
        #     config_file = open(options.config_path)
        # except IOError:
        #     print u"The specified configuration file could not be found."
        #     sys.exit()
        # config = yaml.load(config_file)
        # config_file.close()
        with open(options.config_path) as config_file:
            config = yaml.load(config_file)

        # Append all get_* methods from all models to the list
        # of methods that will always be left untouched.
        # Use a set because it’s fast and avoids duplicates.
        # Q: If the YAML syntax is wrong we will get a confusing
        #    error message here. Should we handle that exception?
        config['ignored_methods'] = set(config['ignored_methods'])
        for model in models.get_models():
            for func_name, func in model.__dict__.items():
                if func_name.startswith('get_'):
                    config['ignored_methods'].add(func_name)

        # Now remove methods from the ignored_methods list that
        # are to be updated despite being actual methods.
        for method in config['force_update']:
            try:
                config['ignored_methods'].remove(method)
            except KeyError:
                pass

        # Remove this key as it’s no longer needed. (This may be overkill.)
        del config['force_update']

        # This is the place to do this, but the execution looks a little
        # wonky. Maybe there is a more graceful way to do this?
        config['template_paths'] = self.create_template_paths(config['template_paths'])

        return config


    def create_template_paths(self, config_paths):
        """
        Generate a complete list of templates to be worked on.

        This is done using one of the following, in this order:

        1. The arguments passed to any --template-path options,
        2. The directories in in TEMPLATE DIRS of the settings
           module (supplied by the --settings option or the
           DJANGO_SETTINGS_MODULE environment variable).

        """
        template_paths = []

        for path in options.template_paths or config_paths or self.settings.TEMPLATE_DIRS:
            # Generally directories will be given to us.
            if os.path.isdir(path):
                for dirpath, dirnames, filenames in os.walk(path):
                    # TODO: exclude .* directories.
                    for filename in filenames:
                        if not filename.startswith('.'):
                            template_paths.append(os.path.join(dirpath, filename))

            # But occasionally someone might hand us a single template file.
            elif os.path.isfile(path):
                template_paths.append(path)

        if not template_paths:
            print u"You either failed to provide any template paths (via the --template-path option, config.template_paths, or settings.TEMPLATE_DIRS), or those you specified do not exist."
            sys.exit()
        return template_paths


    def add_extension(self, line):
        """
        Adds .html extension to all template references.

        The extension ``.html`` will be appended to all template references in
        the form of::

            {% extends "<template>" %}
            {% include "<template>" %}

        thus becoming::

            {% extends "<template>.html" %}
            {% include "<template>.html" %}

        Note that any references that already end with any of the extensions
        listed in config.extensions will be skipped.

        """
        match = self.extension_regex.search(line)

        if match:
            # Note that we are fixing quotes as we go, just to be nice.
            # Single quotes ('') will be replaced with double quotes ("").
            line = self.extension_regex.sub('{% \g<tag> "\g<file_path>.html" %}', line)

        return line


    def update_file_fields(self, line):
        """
        Fix syntax for accessing file field data.

        ================  ============
        Old syntax…       Becomes…
        ----------------  ------------
        get_foo_url       foo.url
        get_foo_size      foo.size
        get_foo_file      foo.file
        get_foo_width     foo.width
        get_foo_height    foo.height
        get_foo_filename  foo.filename
        ================  ============

        All matches will be replaced with the following exceptions:

        1. matches listed in the ignored_methods,
        2. any actual model methods found via settings.INSTALLED_APPS,
           excluding those listed in force_update (because we added the
           actual model methods to the ignored_methods list and then
           removed methods listed in force_update from ignored_methods).

        """
        match = self.file_field_regex.search(line)

        if match:
            if not match.group('field') in self.ignored_methods:
                line = self.file_field_regex.sub('\g<prepend_char>\g<field>.\g<method>', line)

        return line


    def update_relations(self, line):
        """
        Fix references to related objects.

        =============  =============
        Old syntax…    Becomes…
        -------------  -------------
        get_foo        foo
        get_foo_list   foo_set.all
        get_foo_count  foo_set.count
        =============  =============

        All matches will be replaced with the following exceptions:

        1. matches listed in the ignored_methods,
        2. any actual model methods found via settings.INSTALLED_APPS,
           excluding those listed in force_update (because we added the
           actual model methods to the ignored_methods list and then
           removed methods listed in force_update from ignored_methods).

        Note that ``foo_set`` all and count replacements can be customized
        to account for related_name attributes via related_names.

        """
        count_match = self.rel_count_regex.search(line)

        if count_match:
            if not count_match.group('field') in self.ignored_methods:
                line = self.rel_count_regex.sub('\g<prepend_char>\g<field>.count', line)

        list_match = self.rel_list_regex.search(line)

        if list_match:
            if not list_match.group('field') in self.ignored_methods:
                line = self.rel_list_regex.sub('\g<prepend_char>\g<field>.all', line)

        # Do the basic check last.
        basic_match = self.rel_basic_regex.search(line)

        if basic_match:
            if not basic_match.group('field') in self.ignored_methods:
                line = self.rel_basic_regex.sub('\g<prepend_char>\g<field>\g<following_char>', line)

        return line


class ReplacementTestCase(unittest.TestCase):
    def setUp(self):
        self.sample_extension_templates = {
            '{% extends "foo" %}': '{% extends "foo.html" %}',
            '{% extends \'foo\' %}{{ model.foo }}': '{% extends "foo.html" %}{{ model.foo }}',
            '{% extends "foo.html" %}': '{% extends "foo.html" %}',
            '{% extensd "foo" %}': '{% extensd "foo" %}',
            '{% extends foo %}': '{% extends foo %}',
            '{% include "foo" %}': '{% include "foo.html" %}',
            '{% include \'foo\' %}{{ model.foo }}': '{% include "foo.html" %}{{ model.foo }}',
            '{% include "foo.html" %}': '{% include "foo.html" %}',
            '{% inclued "foo" %}': '{% inclued "foo" %}',
            '{% include foo %}': '{% include foo %}',
        }
        self.sample_file_templates = {
            'This is {{ model.get_myfield_url }}': 'This is {{ model.myfield.url }}',
            'This is {{ model.get_myfield_size }}': 'This is {{ model.myfield.size }}',
            'This is {{ model.get_myfield_width }}': 'This is {{ model.myfield.width }}',
            'This is {{ model.get_myfield_height }}': 'This is {{ model.myfield.height }}',
            'This is {{ model.get_myfield_filename }}': 'This is {{ model.myfield.filename }}',
        }
        self.sample_orm_templates = {
            'This is {{ model.get_myfield }}': 'This is {{ model.myfield }}',
            'This is {{ model.get_myfield_count }}': 'This is {{ model.myfield.count }}',
            'This is {{ model.get_myfield_list }}': 'This is {{ model.myfield.all }}',
        }

        self.monkey = TemplateMonkey()

    def test_extensions(self):
        for old_template, new_template in self.sample_extension_templates.items():
            self.assertEqual(self.monkey.add_extension(old_template), new_template)

    def test_files(self):
        for old_template, new_template in self.sample_file_templates.items():
            self.assertEqual(self.monkey.update_file_fields(old_template), new_template)

    def test_orm(self):
        for old_template, new_template in self.sample_orm_templates.items():
            self.assertEqual(self.monkey.update_relations(old_template), new_template)


if __name__ == '__main__':
    usage = """%prog [options]"""
    desc = __doc__

    parser = OptionParser(usage=usage, description=desc)
    parser.add_option('-q', '--quiet',
                                dest='verbosity', action='store_false',
                                help=u"output nothing to the console")
    parser.add_option('-v', '--verbose',
                                dest='verbosity', action='store_true',
                                help=u"output all information to the console")
    parser.add_option('-n', '--dry-run',
                                dest='dry_run', action='store_true',
                                help=u"run everything as normal but don’t save any changes")
    parser.add_option('-x', '--add-extension',
                                dest='add_extension', action='store_true',
                                help=u"add extension “.html” to template references in {% extends %} and {% include %} tags")
    parser.add_option('-f', '--update-file-fields',
                                dest='update_file_fields', action='store_true',
                                help=u"update old file methods to new attributes, i.e. get_foo_url => foo.url, get_foo_size => foo.size, etc.")
    parser.add_option('-r', '--update-relations',
                                dest='update_relations', action='store_true',
                                help=u"update old relation methods to new attributes, i.e. get_bar => bar, get_baz_list => baz_set.all, etc.")
    parser.add_option('-s', '--settings',
                                dest='settings', action='store', default=DJANGO_SETTINGS_MODULE,
                                help=u"use the given settings module (default to $DJANGO_SETTINGS_MODULE)", metavar="settings.module")
    parser.add_option('-t', '--template-path',
                                dest='template_paths', action='append', default=[],
                                help=u"work on the given path (default to settings.TEMPLATE_DIRS)", metavar="/path/to/templates")
    parser.add_option('-c', '--config-yaml',
                                dest='config_path', action='store', default='config.yml', metavar='/path/to/file.yml',
                                help=u"use the specified YAML file for special-case exceptions. (default to config.yml)")
    parser.add_option('-T', '--run-tests',
                                dest='run_tests', action='store_true',
                                help=u"run unit tests for this program")

    (globals()['options'], args) = parser.parse_args()

    if options.run_tests:
        suite = unittest.TestLoader().loadTestsFromTestCase(ReplacementTestCase)
        unittest.TextTestRunner(verbosity=2).run(suite)
    else:
        monkey = TemplateMonkey()
        monkey.port_templates()
