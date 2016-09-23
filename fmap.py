from functools import singledispatch
from types import GeneratorType


def instance(sd, func, arg_type):
    '''
    Register a function as the implementation of a single dispatch
    function sd for a given type.
    i.e instance(fmap, _fmap_my_type, my_type)
    
    This is an alternative to explicitly wrapping the function definition
    in question with @sd.register(arg_type) to allow run-time
    registration and registration of pre-defined functions.
    '''
    # Check that sd is actually a singledispatch function
    if 'dispatch' in dir(sd):
        exec('sd.register(arg_type, func)')
    else:
        # Allow for a public api on `multi` and an implementation on `_multi`
        # as singledispatch is on the type of the first argument only which
        # wont work for all functions.
        try:
            exec('_{}.register(arg_type, func)'.format(sd))
        except:
            raise TypeError(
                '{} is not a single dispatch function'.format(sd)
                )


@singledispatch
def _fmap(col, func):
    '''
    Map a function over a container: default to returning a list
    if no definition can be found for the passed collection type.
    '''
    return [func(element) for element in col]


@_fmap.register(tuple)
def _fmap_tuple(t, func):
    return tuple((func(element) for element in t))


@_fmap.register(dict)
def _fmap_dict_values(d, func):
    '''Apply the function to the values'''
    return {k: func(v) for k, v in d.items()}


@_fmap.register(type({'k': 'v'}.items()))
def _fmap_dict_keys(d_items, func):
    '''Apply the function to the keys'''
    return {func(k): v for k, v in d_items}


@_fmap.register(set)
def _fmap_set(s, func):
    return {func(element) for element in s}


@_fmap.register(bytes)
def _fmap_bytes(b, func):
    return bytes((func(element) for element in b))


@_fmap.register(bytearray)
def _fmap_bytearray(b, func):
    return bytearray((func(element) for element in b))


@_fmap.register(str)
def _fmap_str(s, func):
    return ''.join((func(char) for char in s))


@_fmap.register(type(range(10)))
@_fmap.register(GeneratorType)
def _fmap_lazy_seq(s, func):
    '''Creates a new generator object'''
    for element in s:
        yield func(element)


@_fmap.register(type(None))
def _fmap_none(n, func):
    return None


def fmap(func, col):
    '''
    Apply a function to the elements of a collection and return the
    result as the same collection type.
    NOTE:
        As with normal _map_, _func_ must be a function that takes
        a single argument.

    Supported collection types:
    ```````````````````````````
    list, set, tuple, dict, bytes, bytarray, str, generator, range
    - fmapping over an empty collection will return
      an empty collection of the same type.
    - fmapping over None returns None.
    - For dictionaries there are two ways to use fmap:
        fmap(func, dict)          map over the _values_
        fmap(func, dict.items())  map over the _keys_
    '''
    return _fmap(col, func)
