from copy import copy
from sys import _getframe
from functools import wraps
from collections import Container
from inspect import getfullargspec
from contextlib import contextmanager
from types import CodeType, FunctionType
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


def pattern_matching(func):
    '''
    Allow the programmer to define a function that pattern matches against
    its arguments.

    This supplies a Match_object for each named argument to the original
    function bound to `_arg_name`.
    NOTE: **kwargs will work and each keyword argument can be matched against
          individually or as a dict. *args is bound as a single match object of
          `_args` as that is the only identifier we have to work with.
          (If you prefer to use something like *spam then it will correctly
           bind _spam instead.)
    '''
    def global_to_fast(func):
        '''
        Swap global lookups for local ones for pattern variables and
        match objects. Only works in a decorated function.
        '''
        # cPython Bytecode values for easier readibility of the following code
        HAS_ARGS, LOAD_GLOBAL, LOAD_FAST = 90, 116, 124

        code = func.__code__
        old_ops = (opcode for opcode in code.co_code)
        lvars = code.co_varnames

        templates = [
            c.replace('(', '').replace(')', '').split() for c in code.co_consts
            if isinstance(c, str)
            and (c[0], c[-1]) == ('(', ')')
        ]
        pvars = {p.lstrip('*') for p in sum(templates, [])}

        new_ops = []
        added = 0

        for byte in old_ops:
            if byte > HAS_ARGS:
                # Opcodes > 90 take the next two bytes as args
                lsig, msig = next(old_ops), next(old_ops)
                op = byte

                if byte == LOAD_GLOBAL:
                    index = (msig << 8) + lsig
                    var = code.co_names[index]
                    # We want to swap matched variables: match objects are
                    # already added to the by decorator
                    if var in pvars:
                        # Not removing the entry in co_names as that would
                        # require modifying every other LOAD_GLOBAL index
                        # for vars after this one in co_names...!
                        op = LOAD_FAST
                        lvars += (var,)
                        added += 1
                        lsig, msig = (len(lvars) - 1).to_bytes(2, 'little')
                new_ops.extend([op, lsig, msig])
            else:
                new_ops.append(byte)

        return modify_func(
            func,
            co_code=bytes(new_ops),
            co_varnames=lvars,
            co_nlocals=code.co_nlocals + added)

    def modify_func(func, **kwds):
        '''
        Modifies elements of a function's __code__, retaining the
        original values if no replacement is provided.
        '''
        old = func.__code__
        attrs = ['co_argcount', 'co_kwonlyargcount', 'co_nlocals',
                 'co_stacksize', 'co_flags', 'co_code', 'co_consts',
                 'co_names', 'co_varnames', 'co_filename', 'co_name',
                 'co_firstlineno', 'co_lnotab', 'co_freevars', 'co_cellvars']
        new = CodeType(*(kwds.get(attr, getattr(old, attr)) for attr in attrs))
        return FunctionType(new, func.__globals__, func.__name__,
                            func.__defaults__, func.__closure__)

    func = global_to_fast(func)
    spec = getfullargspec(func)

    @wraps(func)
    def wrapped(*args, **kwargs):
        _globals = copy(func.__globals__)

        for var, val in zip(spec.args, args):
            v = '_{}'.format(var)
            _globals[v] = Match_object(val, decorated=True)
        if spec.varargs:
            v = '_{}'.format(spec.varargs)
            _globals[v] = Match_object(args, decorated=True)
        if spec.varkw:
            for var, val in kwargs.items():
                v = '_{}'.format(var)
                _globals[v] = Match_object(val, decorated=True)
            v = '_{}'.format(spec.varkw)
            _globals[v] = Match_object(kwargs, decorated=True)

        func_w_matchers = FunctionType(func.__code__, _globals)
        return func_w_matchers(*args, **kwargs)

    return wrapped


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
        try:
            next_pvar, next_target = pairs.pop(0)
        except IndexError:
            raise ValueError('FAILED MATCH')

        for _ in range(len(pairs)):
            if next_pvar is None or non_string_collection(next_target):
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
        if rem:
            v, t = pairs.pop(0)
            self.check_match(pvar, t)
        diff = len(pairs) - len(cached) * rem
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
    def __init__(self, val, decorated=False):
        self.val = val
        self.decorated = decorated
        self.map = {}

    def __getitem__(self, key):
        '''
        Provide dict style lookup on the match object for when we
        run outside of cPython and binding to local scope might fail.
        '''
        return self.map[key]

    def __eq__(self, other):
        '''
        Allow for simple direct comparison against values
        '''
        return self.val == other

    def __rshift__(self, type_or_types):
        '''
        `match >> TYPE` perfoms a type check on the bound value
        `match >> (TYPE1, TYPE2...)` returns true if match.val is an
        instance of any of the supplied types.
        '''
        return isinstance(self.val, type_or_types)

    def __ge__(self, pattern_str):
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
            if self.decorated:
                self._bind_to_calling_scope()
            return True
        else:
            print(t.map)
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
        This only works inside of a decorated function; use dict style
        lookup syntax for use in a context manager.
        NOTE: This uses some not-so-nice abuse of stack frames and the
              ctypes API to make this work and as such it will probably
              not run under anything other than cPython.
        '''
        # Grab the stack frame that the caller's code is running in
        frame = _getframe(2)
        # Dump the matched variables and their values into the frame
        frame.f_locals.update(self.map)
        # Force an update of the frame locals from the locals dict
        pythonapi.PyFrame_LocalsToFast(
            py_object(frame),
            c_int(0)
        )
