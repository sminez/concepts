'''
@tcall is a simple tail call optimisation decorator in pure python
You _will_ loose stack frame information for debugging so be warned!
'''
from functools import wraps


def tcall(func):
    '''
    Tail call optimise a function. This decorator will run your function
    in a while loop which can also call out to other functions.
    Any function being called in the tail call position _must_ return a
    tuple of (func, args, kwargs) in order to genreate the tail call:

        `func`      is the next function to be called. Setting this to None
                    will cause the value of args to be returned as the answer.
        `args`      is a tuple of the next positional arguments to the
                    function call.
        `kwargs`    is an optional dictionary of keyword arguments for the
                    next function call.
    '''
    # stash the original function so we can use it in tail calls
    # NOTE: if the user returns "the original" we are actually getting the
    #       decorated version.
    original = func

    @wraps(func)
    def wrapped(*args, **kwargs):
        f = func

        while f:
            result = f(*args, **kwargs)
            try:
                f, *result_or_args = result
                if not callable(f):
                    # we just pulled apart a result
                    return result
            except TypeError:
                # got a raw result so return it
                return result

            # Allow for chained tailcalling functions
            f = f._original if getattr(f, '_tcalling', None) else f

            if len(result_or_args) > 2 or len(result_or_args) == 0:
                raise IndexError(
                    'tcall functions must return (func, args, kwargs)'
                    ' or (func, args)')

            try:
                args, kwargs = result_or_args
            except ValueError:
                args, kwargs = result_or_args[0], {}

    wrapped._tcalling = True
    wrapped._original = original

    return wrapped
