#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
django-template-porting-util: Update Django template syntax from .9x to 1.0.

This program automates much of the process of moving your Django templates from
Django .9x to Django 1.0. It is safe to re-run this program on templates, if
for example, you are porting templates while the old templates are still in use
subject to change. Just put any new templates in the template directory and
re-run. Remember that you can also point to a specific directory, like a
specific directory within your template directory.

"""
__author__ = "Ben Spaulding"
__contributors__ = ["Christian Metts", "Travis Cline"]
__copyright__ = "(c) 2008 Ben Spaulding. GNU GPL 3."
__description__ = "Update Django template syntax from .9x to 1.0."
__url__ = "http://github.com/benspaulding/django-template-porting-util"

import sys, os
from optparse import OptionParser

try:
    from django.conf import settings
    from django.db import models
    from django.template import BLOCK_TAG_START, BLOCK_TAG_END
    from django.template import VARIABLE_TAG_START, VARIABLE_TAG_END
    from django.template import COMMENT_TAG_START, COMMENT_TAG_END
except ImportError:
    print u"Cannot find Django. Did you setup your environment correctly? (Don’t forget to set the DJANGO_SETTINGS_MODULE environment variable.)"
    sys.exit()


class TemplateMonkey:

    def __init__(self, options, args):
        # pass
        self.options = options
        self.args = args
        try:
            # TODO: Am I doing this right? The django.conf.settings and
            #       django.db.models relationship leaves me confused as
            #       to how this needs implemented and when django.db.models
            #       should be imported.
            self.settings = __import__(self.options.settings)
            os.environ["DJANGO_SETTINGS_MODULE"] = self.options.settings
        except ImportError:
            # TODO: Don’t just inform here — prompt and ask for confirmation
            #       to continue. Accidently running this on a template directory
            #       could be disterous.
            print u"Cannot load the specified settings module; using DJANGO_SETTINGS_MODULE environment variable instead."
            self.settings = settings

    def port_templates(self):
        """


        """
        template_list = self.create_template_list()

        config_dict = self.generate_dicts()

        # Now call each method on the list of templates, as needed.
        if self.options.add_extension:
            self.add_extension(template_list)

        if self.options.update_file_fields:
            self.update_file_fields(template_list)

        if self.options.update_relations:
            self.update_relations(template_list)

        if not self.options.add_extension and \
           not self.options.update_file_fields and \
           not self.options.update_relations:
            print u"This monkey won’t do anything unless you tell it to — see available options by running “port-templates.py --help”"


    def create_template_list(self):
        """
        Generate a complete list of templates to be worked on.

        This is done using one of the following, in this order:

        1. The arguments passed to any --template-path options
        2. The directories in in TEMPLATE DIRS of the settings
           module (supplied by the --settings option or the
           DJANGO_SETTINGS_MODULE environment variable).

        """
        template_list = []

        for path in self.options.template_paths or self.settings.TEMPLATE_DIRS:
            # Generally directories will be given to us.
            if os.path.isdir(path):
                for dirpath, dirnames, filenames in os.walk(path):
                    # TODO: exlclude .* directories.
                    for filename in filenames:
                        if not filename.startswith("."):
                            template_list.append(os.path.join(dirpath, filename))

            # But occasionally someone might hand us a single template file.
            elif os.path.isfile(path):
                template_list.append(path)

        # import pprint
        # pp = pprint.PrettyPrinter(indent=4)
        # print pp.pprint(template_list)
        # print u"I created the template list!"
        return template_list
            

    def generate_dicts(self):
        """


        """
        pass
        # 
        # for model in models.get_models():
        #     opts = model._meta
        #     print opts
        #     for field in opts.fields:
        #         print "  f  %s" % field.name
        #     for func_name, func in model.__dict__.items():
        #         try:
        #             if not func_name.startswith("get_"):
        #                 raise StopIteration
        #         except StopIteration:
        #             continue
        #         print "  m  %s" % func_name


    def add_extension(self, template):
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
        listed in config.yml will be skipped.

        """
        print u"I added the extension!"


    def update_file_fields(self, template):
        """Fix syntax for accessing file field data"""
        print u"I updated file fields!"


    def update_relations(self, template):
        """Fix references to related objects"""
        print u"I updated relations!"


if __name__ == "__main__":
    usage = """%prog [options]"""
    desc = __doc__

    parser = OptionParser(usage=usage, description=desc)
    options_array = [
        ["-v", "--verbose", dict(
                                dest="verbose", action="store_true",
                                help=u"output all information to the console")],
        ["-q", "--quiet", dict(
                                dest="verbose", action="store_false",
                                help=u"output nothing to the console")],
        ["-x", "--add-extension", dict(
                                dest="add_extension", action="store_true",
                                help=u"add extension “.html” to template references in {% extends %} and {% include %} tags")],
        ["-f", "--update-file-fields", dict(
                                dest="update_file_fields", action="store_true",
                                help=u"update old file methods to new attributes, i.e. get_baz_url => baz.url, get_baz_size => baz.size, etc.")],
        ["-r", "--update-relations", dict(
                                dest="update_relations", action="store_true",
                                help=u"update old relation methods to new attributes, i.e. get_foo => foo, get_bar_list => bar_set.all, etc.")],
        ["-s", "--settings", dict(
                                dest="settings", action="store", default=os.environ["DJANGO_SETTINGS_MODULE"],
                                help=u"use the given settings module (default to $DJANGO_SETTINGS_MODULE)", metavar="settings.module")],
        ["-t", "--template-path", dict(
                                dest="template_paths", action="append", default=[],
                                help=u"work on the given path (default to settings.TEMPLATE_DIRS)", metavar="/path/to/template(s)")],
        ["-y", "--yaml-config", dict(
                                dest="yaml_config", action="store", default="config.yml", metavar="/path/to/file.yml",
                                help=u"items listed in the given file will not be touched (default to config.yml)")],
    ]

    for s, l, k in options_array:
        parser.add_option(s, l, **k)
    options, args = parser.parse_args()

    monkey = TemplateMonkey(options, args)
    monkey.port_templates()
