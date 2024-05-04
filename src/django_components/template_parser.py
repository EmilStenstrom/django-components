"""
Overrides for the Django Template system to allow finer control over template parsing.

Based on Django Slippers v0.6.2 - https://github.com/mixxorz/slippers/blob/main/slippers/template.py
"""

import re
from typing import Any, Dict, List, Tuple

from django.template.base import (
    FILTER_ARGUMENT_SEPARATOR,
    FILTER_SEPARATOR,
    FilterExpression,
    Parser,
    Variable,
    VariableDoesNotExist,
    constant_string,
)
from django.template.exceptions import TemplateSyntaxError
from django.utils.regex_helper import _lazy_re_compile

######################################################################################################################
# Custom FilterExpression
#
# This is a copy of the original FilterExpression. The only difference is to allow variable names to have extra special
# characters: - : . @ #
######################################################################################################################
filter_raw_string = r"""
^(?P<constant>{constant})|
^(?P<var>[{var_chars}]+|{num})|
 (?:\s*{filter_sep}\s*
     (?P<filter_name>\w+)
         (?:{arg_sep}
             (?:
              (?P<constant_arg>{constant})|
              (?P<var_arg>[{var_chars}]+|{num})
             )
         )?
 )""".format(
    constant=constant_string,
    num=r"[-+\.]?\d[\d\.e]*",
    # The following is the only difference from the original FilterExpression. We allow variable names to have extra
    # special characters: - : . @ #
    var_chars=r"\w\-\:\@\.\#",
    filter_sep=re.escape(FILTER_SEPARATOR),
    arg_sep=re.escape(FILTER_ARGUMENT_SEPARATOR),
)

filter_re = _lazy_re_compile(filter_raw_string, re.VERBOSE)


class ComponentsFilterExpression(FilterExpression):
    def __init__(self, token: str, parser: Parser) -> None:
        # This method is exactly the same as the original FilterExpression.__init__ method, the only difference being
        # the value of `filter_re`.
        self.token = token
        matches = filter_re.finditer(token)
        var_obj = None
        filters: List[Any] = []
        upto = 0
        for match in matches:
            start = match.start()
            if upto != start:
                raise TemplateSyntaxError(
                    "Could not parse some characters: " "%s|%s|%s" % (token[:upto], token[upto:start], token[start:])
                )
            if var_obj is None:
                var, constant = match["var"], match["constant"]
                if constant:
                    try:
                        var_obj = Variable(constant).resolve({})
                    except VariableDoesNotExist:
                        var_obj = None
                elif var is None:
                    raise TemplateSyntaxError("Could not find variable at " "start of %s." % token)
                else:
                    var_obj = Variable(var)
            else:
                filter_name = match["filter_name"]
                args = []
                constant_arg, var_arg = match["constant_arg"], match["var_arg"]
                if constant_arg:
                    args.append((False, Variable(constant_arg).resolve({})))
                elif var_arg:
                    args.append((True, Variable(var_arg)))
                filter_func = parser.find_filter(filter_name)
                self.args_check(filter_name, filter_func, args)
                filters.append((filter_func, args))
            upto = match.end()
        if upto != len(token):
            raise TemplateSyntaxError("Could not parse the remainder: '%s' " "from '%s'" % (token[upto:], token))

        self.filters = filters
        self.var = var_obj
        self.is_var = isinstance(var_obj, Variable)


######################################################################################################################
# Custom token_kwargs
#
# Same as the original token_kwargs, but uses the ComponentsFilterExpression instead of the original FilterExpression.
######################################################################################################################

# Regex for token keyword arguments
kwarg_re = _lazy_re_compile(r"(?:([\w\-\:\@\.\#]+)=)?(.+)")


def token_kwargs(bits: List[str], parser: Parser) -> Dict[str, FilterExpression]:
    """
    Parse token keyword arguments and return a dictionary of the arguments
    retrieved from the ``bits`` token list.

    `bits` is a list containing the remainder of the token (split by spaces)
    that is to be checked for arguments. Valid arguments are removed from this
    list.

    There is no requirement for all remaining token ``bits`` to be keyword
    arguments, so return the dictionary as soon as an invalid argument format
    is reached.
    """
    if not bits:
        return {}
    match = kwarg_re.match(bits[0])
    kwarg_format = match and match[1]
    if not kwarg_format:
        return {}

    kwargs: Dict[str, FilterExpression] = {}
    while bits:
        if kwarg_format:
            match = kwarg_re.match(bits[0])
            if not match or not match[1]:
                return kwargs
            key, value = match.groups()
            del bits[:1]
        else:
            if len(bits) < 3 or bits[1] != "as":
                return kwargs
            key, value = bits[2], bits[0]
            del bits[:3]

        # This is the only difference from the original token_kwargs. We use
        # the ComponentsFilterExpression instead of the original FilterExpression.
        kwargs[key] = ComponentsFilterExpression(value, parser)
        if bits and not kwarg_format:
            if bits[0] != "and":
                return kwargs
            del bits[:1]
    return kwargs


def parse_bits(
    parser: Parser,
    bits: List[str],
    params: List[str],
    name: str,
) -> Tuple[List, Dict]:
    """
    Parse bits for template tag helpers simple_tag and inclusion_tag, in
    particular by detecting syntax errors and by extracting positional and
    keyword arguments.

    This is a simplified version of `django.template.library.parse_bits`
    where we use custom regex to handle special characters in keyword names.
    """
    args = []
    kwargs = {}
    unhandled_params = list(params)
    for bit in bits:
        # First we try to extract a potential kwarg from the bit
        kwarg = token_kwargs([bit], parser)
        if kwarg:
            # The kwarg was successfully extracted
            param, value = kwarg.popitem()
            if param in kwargs:
                # The keyword argument has already been supplied once
                raise TemplateSyntaxError("'%s' received multiple values for keyword argument '%s'" % (name, param))
            else:
                # All good, record the keyword argument
                kwargs[str(param)] = value
                if param in unhandled_params:
                    # If using the keyword syntax for a positional arg, then
                    # consume it.
                    unhandled_params.remove(param)
        else:
            if kwargs:
                raise TemplateSyntaxError(
                    "'%s' received some positional argument(s) after some " "keyword argument(s)" % name
                )
            else:
                # Record the positional argument
                args.append(parser.compile_filter(bit))
                try:
                    # Consume from the list of expected positional arguments
                    unhandled_params.pop(0)
                except IndexError:
                    pass
    if unhandled_params:
        # Some positional arguments were not supplied
        raise TemplateSyntaxError(
            "'%s' did not receive value(s) for the argument(s): %s"
            % (name, ", ".join("'%s'" % p for p in unhandled_params))
        )
    return args, kwargs
