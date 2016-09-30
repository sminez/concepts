from sys import _getframe
from functools import wraps
from collections import Container
from contextlib import contextmanager
from inspect import signature, Parameter
from ctypes import c_int, pythonapi, py_object
from itertools import chain, zip_longest, takewhile


@contextmanager
def pattern_match(target):
    '''
    To make it clear where pattern matching is being attempted and
    to restrict where matched variables can be bound, creation of
    Match_objects is handled by this context manager.

    When the context manager is exited, any matched variables are
    left bound in the local scope but the match object itself is
    explicitly deleted in order to prevent accidental variable
    binding at later points.

    NOTE: Matched variables are bound to the locals of the stack
          frame using this context manager. The binding takes
          place at the point where a successful match is found.
    '''
    matcher = Match_object(target)
    yield matcher
    del matcher


# Experimental: Not currently working!
# def pattern_matching(func):
#     '''
#     Allow the programmer to define a function that pattern matches against
#     its arguments.

#     This will create a compound `match(arg)` context manager that the function
#     is then run inside. This supplies a Match_object for each named argument
#     to the original function bound to `_arg_name`.
#     NOTE: **kwargs will work and each keyword argument can be matched against
#           individually. *args is bound as a single match object of `_args` as
#           that is the only identifier we have to work with.
#           (If you prefer to use something like *spam then it will correctly
#            bind _spam instead.)
#     '''
#     func_sig = signature(func)
#     func_parms = func_sig.parameters.items()
#     starstar_kwargs = Parameter.VAR_KEYWORD

#     def make_manager(var):
#         '''Very simple helper to build the compound context manager'''
#         return 'pattern_match({v}) as _{v}'.format(v=var)

#     @wraps(func)
#     def wrapped(*args, **kwargs):
#         manager_list = []
#         matchers_list = []

#         for name, param in func_parms:
#             if param._kind == starstar_kwargs:
#                for keyword_arg, val in kwargs.items():
#                    manager_list.append(make_manager(keyword_arg))
#                    matchers_list.append(keyword_arg)
#             else:
#                 manager_list.append(make_manager(name))
#                 matchers_list.append(name)

#         bindings = ['{}={}'.format(n[0], p) for n, p in zip(func_parms, args)]

#         exec('\n{}'.join(bindings))

#         manager = 'with {m}: func({a}, **kwargs)'.format(
#             m=', '.join(manager_list),
#             a=', '.join(bindings),
#         )
#         exec(manager)

#     return wrapped
    

def non_string_collection(x):
    '''
    A simple helper to allow string types to be
    distinguished from other collection types.
    '''
    if isinstance(x, Container):
        if not isinstance(x, (str, bytes)):
            return True
    return False


class Pvar:
    '''
    Internal representation of pattern variables.
    Pattern variables maintain
    '''
    __slots__ = 'greedy greedy_expanded symbol value'.split()
    repeating = False

    def __init__(self, symbol, greedy=False):
        self.symbol = symbol
        self.greedy = greedy
        if self.greedy:
            self.symbol = self.symbol.lstrip('*')
            self.greedy_expanded = False
        self.value = None

    def __repr__(self):
        return '{} -> {}'.format(self.symbol, self.value)

    def __eq__(self, other):
        '''
        Compare and bind a value to the pattern variable
        '''
        if self.symbol == '_':
            # Underscores match anything
            self.value = 'Matched'
            return True
        else:
            if non_string_collection(other):
                # Pvars can not match a sub-template
                return False
            elif self.greedy:
                if self.value:
                    # Greedy pattern variables grow
                    self.value.append(other)
                    return True
                else:
                    # Greedy variables always return a list
                    self.value = [other]
                    return True
            else:
                self.value = other
                return True

    def _propagate_match(self, attempt):
        '''
        Make sure repeated variables have the same value.
        '''
        if self.symbol == '_':
            # Don't store values matched against underscores.
            pass
        else:
            existing = attempt.get(self.symbol)

            if existing:
                # This variable is used more than once in the pattern.
                # It must have the same value each time for the match
                # to succeed.
                if self.value != existing:
                    raise ValueError('FAILED MATCH')
            else:
                # There are no conflicts so update the match
                attempt[self.symbol] = self.value


class Template:
    '''
    Specification for the match.
    '''
    __slots__ = 'repeating pvars value map'.split()
    greedy = False

    def __init__(self, match_template):
        self.pvars = []
        self.map = dict()
        self.repeating = False
        self.value = None

        has_star = False
        has_ellipsis = False

        for element in match_template:
            next_var_is_greedy = False

            if non_string_collection(element):
                # Add a sub-template
                self.pvars.append(Template(element))
            else:
                # Tag greedy pattern variables
                if element.startswith('*'):
                    if has_star:
                        raise SyntaxError(
                            'Can only have a max of one * per template')
                    else:
                        has_star = True
                        next_var_is_greedy = True

                if element == '...':
                    # Ellipsis makes the previous sub-template greedy
                    if not isinstance(self.pvars[-1], Template):
                        raise SyntaxError(
                            '... can only be used on a repeating sub template')
                    if has_ellipsis:
                        raise SyntaxError(
                            'Can only have a maximum of one ... per template')
                    else:
                        has_ellipsis = True
                        self.pvars[-1].repeating = True
                else:
                    self.pvars.append(Pvar(element, greedy=next_var_is_greedy))

    def __eq__(self, other):
        if not non_string_collection(other):
            # Convert to a single element list so that we don't accidentally
            # split strings into their characters
            other = [other]

        pairs = list(zip_longest(self.pvars, other, fillvalue=None))
        try:
            return self.compare_and_bind(pairs)
        except ValueError as e:
            if e.args[0] == 'FAILED MATCH':
                return False
            else:
                raise

    def compare_and_bind(self, pairs):
        for _ in range(len(pairs)):
            pvar, target = pairs.pop(0)
            if pvar is None:  # target is longer than the template
                return False

            self.check_match(pvar, target)

            if pvar.greedy and not pvar.greedy_expanded:
                self.match_greedy(pvar, pairs)
                break
            elif pvar.repeating:
                self.match_repeating(pvar, pairs)
                break

        if all([v.value for v in self.pvars]):
            self.value = self.pvars
            return True
        else:
            return False

    def match_greedy(self, pvar, pairs):
        '''
        Deal with a greedy variable in the middle of a pattern by
        caching any later pattern variables as we match and then adding
        them back after expanding the greedy variable to fill the gap.
        '''
        cached = []
        next_pvar, next_target = pairs.pop(0)

        while next_pvar is not None:
            # Keep track of the other pvars in the pattern so
            # they can be used later
            if non_string_collection(next_target):
                break
            cached.append(next_pvar)
            self.check_match(pvar, next_target)
            try:
                next_pvar, next_target = pairs.pop(0)
            except IndexError:
                # End of the list
                break

        # Everything else is unmatched:
        # --> match the last one from the while loop first
        self.check_match(pvar, next_target)
        rem = len(list(takewhile(non_string_collection, pairs)))
        diff = len(pairs) - len(cached) * rem + 1
        pvar.greedy_expanded = True
        left_over_pvars = diff * [pvar] + cached
        left_over_targets = [r[1] for r in pairs]
        new_pairs = list(zip_longest(left_over_pvars, left_over_targets))
        self.compare_and_bind(new_pairs)

    def match_repeating(self, pvar, pairs):
        '''
        Handle a repeating sub-template.
        Variables in sub-templates return a list of all values that
        matched that position in the template.
        '''
        values_so_far = {k: [v] for k, v in pvar.map.items()}
        for _, next_target in pairs:
            # Reset the sub-template match so we can go again
            # This gets transferred to the primary template.
            pvar.map = {}
            for p in pvar.pvars:
                p.value = None
            self.check_match(pvar, next_target)
            # update the map
            for p in pvar.pvars:
                new = values_so_far.setdefault(p.symbol, [])
                new.append(p.value)
        # We've now drained pairs so we are done
        self.map.update(values_so_far)

    def check_match(self, pvar, target):
        '''
        Check for a match and update the current mapping
        This works for Pvars and Templates.
        '''
        if pvar == target:
            if isinstance(pvar, Template):
                if pvar.repeating:
                    for k, v in pvar.map.items():
                        new = self.map.setdefault(k, [])
                        new.append(v)
                else:
                    self.map.update(pvar.map)
            else:
                pvar._propagate_match(self.map)


class Match_object:
    def __init__(self, val):
        self.val = val
        self.map = {}
        
    def __eq__(self, other):
        '''
        Allow for simple direct comparison against values
        '''
        return self.val == other

    def __ge__(self, type_or_types):
        '''
        `match >= TYPE` perfoms a type check on the bound value
        `match >= (TYPE1, TYPE2...)` returns true if match.val is an
        instance of any of the supplied types.
        '''
        return isinstance(self.val, type_or_types)

    def __rshift__(self, pattern_str):
        '''
        Check the supplied pattern against the bound value from the
        context manager. If it matches, bind the pattern variables to
        the values that they matched.
        Returns a bool so that this can be used in an if/else.
        '''
        tokens = pattern_str.replace('(', ' ( ').replace(')', ' ) ').split()
        pattern = next(self.parse(tokens))
        t = Template(pattern)
        if t == self.val:
            self.map = t.map
            self._bind_to_calling_scope()
            return True
        else:
            return False

    def parse(self, tokens):
        '''
        Convert a string representation of the template to
        a - potentially nested - tuple that we can iterate over.
        '''
        tokens = iter(tokens)
        for t in tokens:
           if t == '(':
               group = []
               t = next(tokens)
               if t == ')':
                   raise SyntaxError('Empty match template')
               else:
                   while t != ')':
                       tokens = chain([t], tokens)
                       group.append(next(self.parse(tokens)))
                       t = next(tokens)
                   yield tuple(group)
           else:
               yield t

    def _bind_to_calling_scope(self):
        '''
        Inject the result of a successful match into the calling scope.
        NOTE: This uses some not-so-nice abuse of stack frames and the
              ctypes API to make this work...I'm sorry.
        Stack Frames present when this function is run:
            0: this function
            1: self.__rshift__
            2: the frame in which the user attempted the match
        '''
        # Grab the stack frame that the caller's code is running in
        frame = _getframe(2)
        # Dump the matched variables and their values into the frame
        for var, val in self.map.items():
            frame.f_locals[var] = val
        # Force an update of the frame locals from the locals dict
        pythonapi.PyFrame_LocalsToFast(
            py_object(frame),
            c_int(0)
        )
