# -*- coding: utf-8 -*-
import re
import logging
import copy
from ncm2 import Ncm2Base, getLogger
import vim

logger = getLogger(__name__)


VIM_VAR_NAME = 'g:ncm2_html_subscope_scope'
try:
    SCOPE = vim.eval(VIM_VAR_NAME)
except vim.error:
    # Define default scope and set g:ncm2_html_subscope_scope to the default
    # scope if the global variable doesn't exist
    SCOPE = ['html', 'xhtml', 'php', 'blade', 'jinja',
             'jinja2', 'vue.html.javascript.css', 'vue']
    vim.command('let {} = {}'.format(VIM_VAR_NAME, SCOPE))


class SubscopeDetector(Ncm2Base):

    scope = SCOPE

#     def sub_context(self, ctx, src):
    def detect(self, lnum, ccol, src):

        from html.parser import HTMLParser

        scoper = self

        class MyHTMLParser(HTMLParser):

            last_data_start = None
            last_data = None

            scope_info = None
            skip = False

            def handle_starttag(self, tag, attrs):

                self.skip = False

                if tag in ['style', 'script']:
                    for attr in attrs:
                        try:
                            # avoid css completion for lang="stylus"
                            if tag == 'style' and attr[0] == 'lang' and attr[1] and attr[1] not in ['css', 'scss']:
                                self.skip = True
                                return
                            if tag == 'style' and attr[0] == 'type' and attr[1] and attr[1] not in ['text/css']:
                                self.skip = True
                                return
                            if tag == 'script' and attr[0] == 'type' and attr[1] and attr[1] not in ['text/javascript']:
                                self.skip = True
                                return
                        except:
                            pass

            def handle_endtag(self, tag):

                if self.skip:
                    return

                if tag in ['style', 'script']:

                    startpos = self.last_data_start
                    endpos = self.getpos()
                    if ((startpos[0] < lnum
                         or (startpos[0] == lnum
                                 and startpos[1]+1 <= ccol))
                            and
                            (endpos[0] > lnum
                             or (endpos[0] == lnum
                                 and endpos[1] >= ccol))
                        ):

                        self.scope_info = {}
                        self.scope_info['lnum'] = lnum-startpos[0]+1
                        if lnum == startpos[0]:
                            self.scope_info['ccol'] = ccol-(startpos[1]+1)+1
                        else:
                            self.scope_info['ccol'] = ccol

                        if tag == 'script':
                            self.scope_info['scope'] = 'javascript'
                        else:
                            # style
                            self.scope_info['scope'] = 'css'

                        self.scope_info['scope_offset'] = scoper.lccol2pos(
                            startpos[0], startpos[1]+1, src)
                        self.scope_info['scope_len'] = len(self.last_data)

                        # offset as lnum, ccol format
                        self.scope_info['scope_lnum'] = startpos[0]
                        # startpos[1] is zero based
                        self.scope_info['scope_ccol'] = startpos[1]+1

            def handle_data(self, data):
                self.last_data = data
                self.last_data_start = self.getpos()

        parser = MyHTMLParser()
        parser.feed(src)
        if parser.scope_info:

            new_ctx = {}
            new_ctx['scope'] = parser.scope_info['scope']
            new_ctx['lnum'] = parser.scope_info['lnum']
            new_ctx['ccol'] = parser.scope_info['ccol']

            new_ctx['scope_offset'] = parser.scope_info['scope_offset']
            new_ctx['scope_len'] = parser.scope_info['scope_len']
            new_ctx['scope_lnum'] = parser.scope_info['scope_lnum']
            new_ctx['scope_ccol'] = parser.scope_info['scope_ccol']

            return new_ctx

        pos = self.lccol2pos(lnum, ccol, src)

        # css completions for style='|'
        for match in re.finditer(r'style\s*=\s*("|\')(.*?)\1', src):
            if match.start(2) > pos:
                return
            if match.end(2) < pos:
                continue
            # start < pos and and>=pos
            new_src = match.group(2)

            new_ctx = {}
            new_ctx['scope'] = 'css'

            new_ctx['scope_offset'] = match.start(2)
            new_ctx['scope_len'] = len(new_src)
            lccol = self.pos2lccol(match.start(2), src)
            new_ctx['scope_lnum'] = lccol[0]
            new_ctx['scope_ccol'] = lccol[1]

            sub_pos = pos - match.start(2)
            lccol = self.pos2lccol(sub_pos, new_src)
            logger.debug('sub_pos %s new_src %s lnum ccol %s', sub_pos, new_src, lccol)
            new_ctx['lnum'] = lccol[0]
            new_ctx['ccol'] = lccol[1]
            return new_ctx

        return None
