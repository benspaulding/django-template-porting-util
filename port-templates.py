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
you use some for of version control or at least make backups of your files
before every use.

"""
# Note that __future__ imports must go at the top.
from __future__ import with_statement

__author__ = "Ben Spaulding"
__contributors__ = []
__copyright__ = "(c) 2008 Ben Spaulding. GNU GPL 3."
__description__ = "Update Django template syntax from .9x to 1.0."
__url__ = "http://github.com/benspaulding/django-template-porting-util"

import sys, os, pprint, yaml
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
        self.options = options
        # Q: Do I need args here? Don’t know when or why I would use them.
        self.args = args
        try:
            # Q: Am I doing this right? The django.conf.settings and
            #    django.db.models relationship leaves me confused as
            #    to how this needs implemented and when django.db.models
            #    should be imported.
            self.settings = __import__(self.options.settings)
            os.environ["DJANGO_SETTINGS_MODULE"] = self.options.settings
        except ImportError:
            # TODO: Don’t just inform here — prompt and ask for confirmation
            #       to continue. Accidently running this on a template directory
            #       could be disterous.
            print u"Cannot load the specified settings module; using DJANGO_SETTINGS_MODULE environment variable instead."
            self.settings = settings
        # Q: Should the config keys and template_paths be added as
        #    attrs to the class here? Dunno.
        # Q: Does this belong here? I’m thinking of verbosity.
        # self.pprinter = pprint.PrettyPrinter(indent=2)

    def port_templates(self):
        """Run requested methods on the specified templates."""

        if not self.options.add_extension and \
           not self.options.update_file_fields and \
           not self.options.update_relations:
            print u"This monkey won’t do anything unless you tell it to — see available options by running “port-templates.py --help”"
            sys.exit()

        template_paths = self.create_template_paths()
        config = self.load_config()

        for template_path in template_paths:
            # Using “with” statements with file objcts is good practice, per
            # http://docs.python.org/tutorial/inputoutput.html
            # Note that “with” statements had to be enabled in Python 2.5. See
            # http://docs.python.org/whatsnew/2.5.html#pep-343-the-with-statement
            with open(template_path, 'r+') as template:
                for line in template:
                    # Now call each method on every line of the template, as needed.
                    # Q: Do I need to flush anywhere for this to work?
                    if self.options.add_extension:
                        self.add_extension(line)
                    if self.options.update_file_fields:
                        self.update_file_fields(line)
                    if self.options.update_relations:
                        self.update_relations(line)
                # TODO: Here (I believe) is where I need to write each line
                #       back to the template file. How?
                # template.write(template)
                template.close()


    def create_template_paths(self):
        """
        Generate a complete list of templates to be worked on.

        This is done using one of the following, in this order:

        1. The arguments passed to any --template-path options,
        2. The directories in in TEMPLATE DIRS of the settings
           module (supplied by the --settings option or the
           DJANGO_SETTINGS_MODULE environment variable).

        """
        template_paths = []

        for path in self.options.template_paths or self.settings.TEMPLATE_DIRS:
            # Generally directories will be given to us.
            if os.path.isdir(path):
                for dirpath, dirnames, filenames in os.walk(path):
                    # TODO: exlclude .* directories.
                    for filename in filenames:
                        if not filename.startswith("."):
                            template_paths.append(os.path.join(dirpath, filename))

            # But occasionally someone might hand us a single template file.
            elif os.path.isfile(path):
                template_paths.append(path)

        if not template_paths:
            print u"You either failed to provide any template paths (via settings.TEMPLATE_DIRS or the --template-path option), or those you specified do not exist."
            sys.exit()
        return template_paths
            

    def load_config(self):
        """
        Create configuration dictionary from various sources.

        Loads the specified YAML configuration file and adds all
        methods found on any model in settings.INSTALLED_APPS to
        the config.relations.ignored_methods list. 

        """
        # Q: Do I need exception handline for the file stuff?
        config_file = open(self.options.config_path)
        config = yaml.load(config_file)
        config_file.close()

        # Append all get_* methods from all models to the list
        # of methods that will always be left untouched.
        for model in models.get_models():
            for func_name, func in model.__dict__.items():
                if func_name.startswith("get_"):
                    config['relations']['ignored_methods'].append(func_name)

        # Remove duplicate methods, just to be tidy.
        # Done via a dictionary because it’s faster; see
        # http://pyfaq.infogami.com/how-do-you-remove-duplicates-from-a-list
        d = {}
        for method in config['relations']['ignored_methods']:
            d[method]=method

        # Now remove methods from the ignored_methods list that
        # are to be updated despite being actual methods.
        for method in config['relations']['force_update']:
            del d[method]
        # Remove this key as it’s no longer needed.
        del config['relations']['force_update']

        # Now put the cleaned-up dictionary values back into our list.
        config['relations']['ignored_methods'] = d.values()
        return config


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
        # Use regex fu on the line.
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

        1. matches listed in the config.relations.ignored_methods,
        2. any actual model methods found via settings.INSTALLED_APPS,
           excluding those listed in config.relations.force_update.

        """
        # Use regex fu on the line.
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

        1. matches listed in the config.relations.ignored_methods,
        2. any actual model methods found via settings.INSTALLED_APPS,
           excluding those listed in config.relations.force_update.

        Note that ``foo_set`` all and count replacements can be customized
        to account for related_name attributes via config.relations.mapping.

        """
        # Use regex fu on the line.
        return line


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
        ["-n", "--dry-run", dict(
                                dest="dry_run", action="store_true",
                                help=u"run everything as normal but don’t save any changes")],
        ["-x", "--add-extension", dict(
                                dest="add_extension", action="store_true",
                                help=u"add extension “.html” to template references in {% extends %} and {% include %} tags")],
        ["-f", "--update-file-fields", dict(
                                dest="update_file_fields", action="store_true",
                                help=u"update old file methods to new attributes, i.e. get_foo_url => foo.url, get_foo_size => foo.size, etc.")],
        ["-r", "--update-relations", dict(
                                dest="update_relations", action="store_true",
                                help=u"update old relation methods to new attributes, i.e. get_bar => bar, get_baz_list => baz_set.all, etc.")],
        ["-s", "--settings", dict(
                                dest="settings", action="store", default=os.environ["DJANGO_SETTINGS_MODULE"],
                                help=u"use the given settings module (default to $DJANGO_SETTINGS_MODULE)", metavar="settings.module")],
        ["-t", "--template-path", dict(
                                dest="template_paths", action="append", default=[],
                                help=u"work on the given path (default to settings.TEMPLATE_DIRS)", metavar="/path/to/templates")],
        ["-y", "--yaml-config", dict(
                                dest="config_path", action="store", default="config.yml", metavar="/path/to/file.yml",
                                help=u"use the specified YAML file for special-case exceptions. (default to config.yml)")],
    ]

    for s, l, k in options_array:
        parser.add_option(s, l, **k)
    options, args = parser.parse_args()

    monkey = TemplateMonkey(options, args)
    monkey.port_templates()
