#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import unittest
from optparse import OptionParser
DJANGO_SETTINGS_MODULE = os.environ["DJANGO_SETTINGS_MODULE"]
from port_templates import TemplateMonkey


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
        
        usage = """%prog [options]"""
        desc = __doc__

        parser = OptionParser(usage=usage, description=desc)
        parser.add_option("-q", "--quiet",
                                    dest="verbosity", action="store_false",
                                    help=u"output nothing to the console")
        parser.add_option("-v", "--verbose",
                                    dest="verbosity", action="store_true",
                                    help=u"output all information to the console")
        parser.add_option("-n", "--dry-run",
                                    dest="dry_run", action="store_true",
                                    help=u"run everything as normal but don’t save any changes")
        parser.add_option("-x", "--add-extension",
                                    dest="add_extension", action="store_true",
                                    help=u"add extension “.html” to template references in {% extends %} and {% include %} tags")
        parser.add_option("-f", "--update-file-fields",
                                    dest="update_file_fields", action="store_true",
                                    help=u"update old file methods to new attributes, i.e. get_foo_url => foo.url, get_foo_size => foo.size, etc.")
        parser.add_option("-r", "--update-relations",
                                    dest="update_relations", action="store_true",
                                    help=u"update old relation methods to new attributes, i.e. get_bar => bar, get_baz_list => baz_set.all, etc.")
        parser.add_option("-s", "--settings",
                                    dest="settings", action="store", default=DJANGO_SETTINGS_MODULE,
                                    help=u"use the given settings module (default to $DJANGO_SETTINGS_MODULE)", metavar="settings.module")
        parser.add_option("-t", "--template-path",
                                    dest="template_paths", action="append", default=[],
                                    help=u"work on the given path (default to settings.TEMPLATE_DIRS)", metavar="/path/to/templates")
        parser.add_option("-c", "--config-yaml",
                                    dest="config_path", action="store", default="config.yml", metavar="/path/to/file.yml",
                                    help=u"use the specified YAML file for special-case exceptions. (default to config.yml)")

        (globals()["options"], args) = parser.parse_args()

        # Mock. Grr.
        TemplateMonkey.create_template_paths = lambda self, x: []

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
    unittest.main()
