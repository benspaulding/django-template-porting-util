#!/usr/bin/env python
"""
Remove the magic from a directory of templates.

The following transformations are performed, unless explicitally turned off:

    - Modifies {% extends %} and {% include %} to explicitally use the ".html"
      extension (display with '--skip-extension-addition').
      
      (see http://code.djangoproject.com/wiki/RemovingTheMagic#Includetemplateextensionexplicitly)
      
    - Changes variables (and variables in tags) of the form {{
      foo.get_bar_list }} to {{ foo.bar_set.all }} (disable with
      '--skip-relation-renaming'). 
      
      This doesn't rename {{ foo.get_bar }} because it has no way of knowing
      if that's a relation that got renamed or a function that didn't.
      
      (see http://code.djangoproject.com/wiki/RemovingTheMagic#Descriptorfields).
      
    - Rename templates that look like they're generic templates named in
      the old way (i.e. "blog/entries_detail.html" instead of
      "blog/entry_detail.html"). Since this is bound to be inacurate,
      the new set of templates will include *both* the old name and a guess at
      the new one (display with '--skip-generic-template-renaming').
      
Because of the complexity of many templates that's can't possibly be perfect.
You'll of course want to double-check the output to make sure that everything's
OK (and to take care of renamed FK lookups, too).
"""

import os
import re
import shutil

# The following template variables are coppied from django.template to avoid 
# a sticky dependacy when running this script.

BLOCK_TAG_START = '{%'
BLOCK_TAG_END = '%}'
VARIABLE_TAG_START = '{{'
VARIABLE_TAG_END = '}}'

# match a variable or block tag and capture the entire tag, including start/end delimiters
tag_re = re.compile('(%s.*?%s|%s.*?%s)' % (re.escape(BLOCK_TAG_START), re.escape(BLOCK_TAG_END),
                                          re.escape(VARIABLE_TAG_START), re.escape(VARIABLE_TAG_END)))

class TemplateUpdater:
    
    def __init__(self, old, new, options):
        self.old, self.new, self.options = old, new, options
        
    def update_templates(self):
        for root, dirs, files in os.walk(self.old):
            self.handle_directory('', root, files)
            if '.svn' in dirs:
                dirs.remove('.svn') 

    def handle_directory(self, arg, dirname, names):
        """callback for os.walk"""
        
        # figure out the name of the matching new directory
        new_dirname = os.path.join(self.new, dirname.replace(self.old, '').strip(os.path.sep))
        if self.options.verbosity == 2:
            print "--- Directory: '%s' ---" % new_dirname

        # create the new dir if it doesn't exist
        if not os.path.exists(new_dirname):
            os.makedirs(new_dirname)
            
        print names
        # handle all the things in the directory
        for name in names:
            print name
            # strip any dot-prefixed dirs out of the remaining things to be handled
            if not name.startswith('.'):
                # parse and move any ".html" templates
                if os.path.splitext(name)[1] == ".html":
                    self.handle_template(dirname, new_dirname, name)
                
                # simply copy any other files
                elif os.path.isfile(os.path.join(dirname, name)):
                    if self.options.verbosity == 2:
                        print "Copy non-template to '%s'" % os.path.join(new_dirname, name)
                    shutil.copy(os.path.join(dirname, name), os.path.join(new_dirname, name))

        if self.options.verbosity == 2:
            print

    def handle_template(self, old_directory, new_directory, template_name):
        """handle each template as it comes 'off the line'"""
                
        # read the old template
        new_template = open(os.path.join(old_directory, template_name)).read()
        
        # handle each bit of updating (of requested)
        if not options.skip_extension_addition:
            new_template = self.add_extensions(new_template)
        if not options.skip_relation_renaming:
            new_template = self.rename_relations(new_template)
        if not options.skip_generic_template_renaming:
            self.handle_possible_generic_template_names(old_directory, new_directory, template_name, new_template)
        if not options.skip_file_renaming:
            new_template = self.handle_file_renaming(new_template)
        # write out the new template
        if self.options.verbosity == 2:
            print "Create template '%s'" % os.path.join(new_directory, template_name)
        fp = open(os.path.join(new_directory, template_name), 'w')
        fp.write(new_template)
        fp.close()
            
    def add_extensions(self, template_text):
        """add ".html" extensions to {% extends %} and {% include %} tags"""
        
        new_template = []
        
        for token in filter(None, tag_re.split(template_text)):
            if token.startswith(BLOCK_TAG_START):
                tag_contents = token[len(BLOCK_TAG_START):-len(BLOCK_TAG_END)].strip()
                if tag_contents.startswith("extends") or tag_contents.startswith("include"):
                    # these should be of the form {% extends <arg %}, but we
                    # ignore anything that's not for some reason
                    command, arg = tag_contents.split(' ', 1)
                    
                    # If the argument is a string (and not a var) then add
                    # the ".html" onto the template name (replacing the old
                    # token)
                    if arg.startswith("'") or arg.startswith('"'):
                        token = '%s %s %s%s.html%s %s' % \
                            (BLOCK_TAG_START, command, arg[0], arg[1:-1], arg[0], BLOCK_TAG_END)
            
            new_template.append(token)
        return ''.join(new_template)
    
    # map old relation names to new ones -- order matters here
    RELATION_RENAME_MAP = (
        (r"get_(\w+)(_list)",    r"\1_set.all"), 
        (r"get_(\w+)(_count)",   r"\1.count"), 
    )
        
    def rename_relations(self, template_text):
        """
        rename relations (i.e. foo.get_bar_list -> foo.bar_set.all,
        foo.get_spam_count --> foo.spam_set.count, etc.)
        """
        
        new_template = []
        
        for token in filter(None, tag_re.split(template_text)):
            # always apply the replacements within variables
            if token.startswith(VARIABLE_TAG_START):
                for (pat, repl) in self.RELATION_RENAME_MAP:
                    token = re.sub(pat, repl, token)
            
            # However, in tags we only want to apply the transform starting 
            # with the second bit -- that avoids spurious replacements with
            # tags like {% get_comment_list %}
            elif token.startswith(BLOCK_TAG_START):
                tag_contents = token[len(BLOCK_TAG_START):-len(BLOCK_TAG_END)].strip()
                if tag_contents.count(' ') >= 1:
                    command, arg = tag_contents.split(' ', 1)
                    for (pat, repl) in self.RELATION_RENAME_MAP:
                        arg = re.sub(pat, repl, arg)
                    token = "%s %s %s %s" % (BLOCK_TAG_START, command, arg, BLOCK_TAG_END)
                
            new_template.append(token)
            
        return ''.join(new_template)

    def handle_file_renaming(self, template_text):
        """
        Handle file renaming from the file storage refactoring (hopefully).
        """
        
        new_template = []
        FILE_RENAME_MAP = (
            (r"(get)_(\w+)_(filename)", r"\2.path"),
            (r"(get)_(\w+)_(url)", r"\2.url"),
            (r"(get)_(\w+)_(size)", r"\2.size"),
            (r"(save)_(\w+)_(file)", r"\2.save"),
            (r"(get)_(\w+)_(width)", r"\2.width"),
            (r"(get)_(\w+)_(height)", r"\2.height"),
        )
        for token in filter(None, tag_re.split(template_text)):
            if token.startswith(VARIABLE_TAG_START) or token.startswith(BLOCK_TAG_START):
                for (pat, repl) in FILE_RENAME_MAP:
                    if re.search(pat, token) and re.search(pat, token).groups()[1] != 'absolute':
                        token = re.sub(pat, repl, token)
            new_template.append(token)
        return ''.join(new_template)
        
    def handle_possible_generic_template_names(self, old_directory, new_directory, template_name, template_text):
        """
        Possibly write out a new slightly different named template which
        complies with the new generic template name semantics
        """
        full_path = os.path.join(old_directory, template_name)
        relative_template_path = full_path.replace(self.old, "").strip(os.path.sep)
        if relative_template_path.count(os.path.sep) == 1 and template_name.split('_')[0].endswith('s'):
            new_template_name = template_name.split('_')[0][:-1] + "_" + "_".join(template_name.split('_', 1)[1:])
            new_template_destination = os.path.join(new_directory, new_template_name)
            if options.verbosity > 0:
                print "Generic template '%s'; creating renamed copy at '%s'" % \
                    (relative_template_path, new_template_destination)
            fp = open(new_template_destination, 'w')
            fp.write(template_text)
            fp.close()

if __name__ == '__main__':
    import optparse
    parser = optparse.OptionParser(usage="%prog [options] template_directory")
    parser.add_option('-q', '--quiet', action="store_const", dest="verbosity", const=0, help="Be vewy qwiet")
    parser.add_option('-v', '--verbose', action="store_const", dest="verbosity", const=2, help="Announce all actions loudly")
    parser.add_option('-o', '--output', help='Directory to put updated templates into (default to "$OLD.new")')
    parser.add_option('-x', '--skip-extension-addition', action='store_true', default=False)
    parser.add_option('-r', '--skip-relation-renaming', action='store_true', default=False)
    parser.add_option('-g', '--skip-generic-template-renaming', action='store_true', default=False)
    parser.add_option('-f', '--skip-file-renaming', action='store_true', default=False)
    
    options, args = parser.parse_args()
    if len(args) != 1:
        parser.error("Wrong number of arguments")
    old = os.path.abspath(args[0])
    if options.output:
        new = options.output
    else:
        new = old + ".new"
    if not os.path.exists(new):
        os.mkdir(new)
        
    updater = TemplateUpdater(old, new, options)
    updater.update_templates()