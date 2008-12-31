#!/usr/bin/env python
"""django-template-porting-util: Update Django template syntax from .9x to 1.0."""
__author__ = "Ben Spaulding"
__contributors__ = ["Christian Metts", "Daniel Lindsley", "Travis Cline"]
__copyright__ = "(c) 2008 Ben Spaulding. GNU GPL 3."
__description__ = "Update Django template syntax from .9x to 1.0."
__url__ = "http://github.com/benspaulding/django-template-porting-util"

import sys
from optparse import OptionParser

try:
    from django.conf import settings
    from django.db import models
except ImportError:
    print "Cannot find Django files. Did you setup your environment correctly?"
    sys.exit()


class TemplateMonkey:

    def __init__(self, options, args):
        pass

    def port_templates(self):
        """"""
        for model in models.get_models():
            opts = model._meta
            print opts
            for field in opts.fields:
                print "  f  %s" % field.name
            for func_name, func in model.__dict__.items():
                try:
                    if not func_name.startswith('get_'):
                        raise StopIteration
                except StopIteration:
                    continue
                print "  m  %s" % func_name

    def add_extension(self):
        """
        Add ``.html`` to all template references

        

        """
        pass

    def update_relations(self):
        """"""
        pass

    def update_files(self):
        """"""
        pass


if __name__ == '__main__':
    usage = """%prog [options]"""
    desc = """This program automates much of the process of moving your Django
templates from Django .9x to Django 1.0. It is safe to re-run this program on
templates, if for example, you are porting templates while the old templates
are still in use subject to change. Just put any new templates in the template
directory and re-run. Remember that you can also point to a specific directory,
like a specific directory within your template directory."""

    parser = OptionParser(usage=usage, description=desc)
    options_array = [
        ["-v", "--verbose", dict(
                                dest="verbose", action="store_true",
                                help="output all information to the console")],
        ["-q", "--quiet", dict(
                                dest="verbose", action="store_false",
                                help="output nothing to the console")],
        ["-x", "--add-template-extension", dict(
                                dest="add_template_extension", action="store_true",
                                help="add ``.html`` to all templates referenced in {% extends %} and {% include %} tags")],
        ["-r", "--update-relations", dict(
                                dest="update_relations", action="store_true",
                                help="update old relation methods to new attributes, i.e. get_foo => foo, get_bar_list => bar.all, etc.")],
        ["-f", "--update-files", dict(
                                dest="update_files", action="store_true",
                                help="update old file methods to new attributes, i.e. get_baz_url => baz.url, get_baz_size => baz.size, etc.")],
        ["-s", "--settings", dict(
                                dest="settings", action="store",
                                help="use the given settings module", metavar="settings.module")],
        ["-t", "--template-dir", dict(
                                dest="template_dirs", action="append", default=[],
                                help="use the given template directory", metavar="/path/to/templates")],
    ]

    for s, l, k in options_array:
        parser.add_option(s, l, **k)
    options, args = parser.parse_args()

    monkey = TemplateMonkey(options, args)
    monkey.port_templates()
