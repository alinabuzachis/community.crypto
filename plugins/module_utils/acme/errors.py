# -*- coding: utf-8 -*-

# Copyright: (c) 2016 Michael Gruener <michael.gruener@chaosmoon.net>
# Copyright: (c) 2021 Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


def format_error_problem(problem, subproblem_prefix=''):
    if 'title' in problem:
        msg = 'Error "{title}" ({type})'.format(
            type=problem['type'],
            title=problem['title'],
        )
    else:
        msg = 'Error {type}'.format(type=problem['type'])
    if 'detail' in problem:
        msg += ': "{detail}"'.format(detail=problem['detail'])
    subproblems = problem.get('subproblems')
    if subproblems is not None:
        msg = '{msg} Subproblems:'.format(msg=msg)
        for index, problem in enumerate(subproblems):
            index_str = '{prefix}{index}'.format(prefix=subproblem_prefix, index=index)
            msg = '{msg}\n({index}) {problem}.'.format(
                msg=msg,
                index=index_str,
                problem=format_error_problem(problem, subproblem_prefix='{0}.'.format(index_str)),
            )
    return msg


class ModuleFailException(Exception):
    '''
    If raised, module.fail_json() will be called with the given parameters after cleanup.
    '''
    def __init__(self, msg, **args):
        super(ModuleFailException, self).__init__(self, msg)
        self.msg = msg
        self.module_fail_args = args

    def do_fail(self, module, **arguments):
        module.fail_json(msg=self.msg, other=self.module_fail_args, **arguments)


class ACMEProtocolException(ModuleFailException):
    def __init__(self, module, msg=None, info=None, response=None, content=None, content_json=None):
        # Try to get hold of content, if response is given and content is not provided
        if content is None and content_json is None and response is not None:
            try:
                content = response.read()
            except AttributeError:
                content = info.pop('body', None)

        # Try to get hold of JSON decoded content, when content is given and JSON not provided
        if content_json is None and content is not None:
            try:
                content_json = module.from_json(content.decode('utf8'))
            except Exception:
                pass

        extras = dict()
        url = info['url'] if info else None
        code = info['status'] if info else None
        extras['http_url'] = url
        extras['http_status'] = code

        if msg is None:
            msg = 'ACME request failed'
        add_msg = ''

        if code >= 400 and content_json is not None and 'type' in content_json:
            if 'status' in content_json and content_json['status'] != code:
                code = 'status {problem_code} (HTTP status: {http_code})'.format(http_code=code, problem_code=content_json['status'])
            else:
                code = 'status {problem_code}'.format(problem_code=code)
            add_msg = ' {problem}.'.format(problem=format_error_problem(content_json))

            subproblems = content_json.pop('subproblems', None)
            extras['problem'] = content_json
            extras['subproblems'] = subproblems or []
            if subproblems is not None:
                add_msg = '{add_msg} Subproblems:'.format(add_msg=add_msg)
                for index, problem in enumerate(subproblems):
                    add_msg = '{add_msg}\n({index}) {problem}.'.format(
                        add_msg=add_msg,
                        index=index,
                        problem=format_error_problem(problem, subproblem_prefix='{0}.'.format(index)),
                    )
        else:
            code = 'HTTP status {code}'.format(code=code)
            if content_json is not None:
                add_msg = ' The JSON error result: {content}'.format(content=content_json)
            elif content is not None:
                add_msg = ' The raw error result: {content}'.format(content=content.decode('utf-8'))

        super(ACMEProtocolException, self).__init__(
            '{msg} for {url} with {code}.{add_msg}'.format(msg=msg, url=url, code=code, add_msg=add_msg),
            **extras
        )
        self.problem = {}
        self.subproblems = []
        for k, v in extras.items():
            setattr(self, k, v)


class BackendException(ModuleFailException):
    pass


class NetworkException(ModuleFailException):
    pass


class KeyParsingError(ModuleFailException):
    pass
