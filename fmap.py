from types import GeneratorType
from collections import Iterator, deque, defaultdict, \
        Counter, OrderedDict, ChainMap

from .dispatch import dispatch_on


@dispatch_on(index=1)
def fmap(func, col):
    '''
    Map a function over the elements of a container.
    If no specific implementation is found for the supplied type then
    a TypeError is raised along with a description of how to add a case.

    NOTE: As with normal _map_, _func_ must be a function that takes
          a single argument. (Dictionaries are a special case, see below)

    Supported collection types:
    ```````````````````````````
    list, set, tuple, dict, bytes, bytarray, str, generator, range
    - fmapping over an empty collection will return
      an empty collection of the same type.
    - fmapping over None returns None.
    - For dictionaries there are two ways to use fmap:
        fmap(func, dict)           map over the _values_
        fmap(on_keys(func), dict)  map over the _keys_
        fmap(func, dict)           map over both if func accepts and returns
                                   two values
    '''
    # Allow raw iterators to be mapped over and return an iterator here as
    # there is no single `iterator` type to check against.
    if isinstance(col, Iterator):
        for element in col:
            yield func(element)
    else:
        # Everything else requires its own definition
        msg = ('fmap is not currently defined for {t}.\n To add a'
               ' definition, use the @fmap_for({t}) decorator.\n'
               ' (See the fmap README for examples)')
        raise TypeError(msg.format(t=type(col)))


fmap_for = fmap.add


#########################################################################
# Helpers for fmapping over dicts: apply to the function being fmapped: #
# i.e. fmap(on_keys(times2), {str(n): n for n in range(10)})            #
#      fmap(on_values(times2), {str(n): n for n in range(10)})          #
#########################################################################
def on_keys(func):
    def composed(key, value):
        return func(key), value
    return composed


def on_values(func):
    def composed(key, value):
        return key, func(value)
    return composed


######################################
# Implementations for built in types #
######################################
@fmap_for(type(None))
def _fmap_none(func, n):
    return None


@fmap_for(range)
@fmap_for(GeneratorType)
def _fmap_lazy_seq(func, s):
    for element in s:
        yield func(element)


@fmap_for(list)
def _fmap_list(func, l):
    return list(map(func, l))


@fmap_for(tuple)
def _fmap_tuple(func, t):
    return tuple(map(func, t))


@fmap_for(set)
def _fmap_set(func, s):
    return set(map(func, s))


@fmap_for(dict)
def _fmap_dict(func, d):
    '''
    If this is a function on single values, apply it to
    the values in the dictionary. Otherwise, assume that
    it is a function that takes a tuple of two values and
    returns a tuple of two values.
        (Also see `on_values` and `on_keys`)
    '''
    if func.__code__.co_argcount == 1:
        func = on_values(func)
    fmapped = (func(k, v) for k, v in d.items())
    return {k: v for k, v in fmapped}


@fmap_for(str)
def _fmap_str(func, s):
    return ''.join(map(func, s))


@fmap_for(bytes)
def _fmap_bytes(func, b):
    return bytes(map(func, b))


@fmap_for(bytearray)
def _fmap_bytearray(func, b):
    return bytearray(map(func, b))


# Implementations for the collections module
@fmap_for(deque)
def _fmap_deque(func, d):
    return deque(map(func, d))


@fmap_for(Counter)
def _fmap_counter(func, c):
    if func.__code__.co_argcount == 1:
        func = on_values(func)

    fmapped = (func(k, v) for k, v in c.items())
    return Counter({k: v for k, v in fmapped})


@fmap_for(OrderedDict)
def _fmap_ordered_dict(func, o):
    if func.__code__.co_argcount == 1:
        func = on_values(func)

    fmapped = (func(k, v) for k, v in o.items())
    return OrderedDict(fmapped)


@fmap_for(ChainMap)
def _fmap_chain_map(func, c):
    if func.__code__.co_argcount == 1:
        func = on_values(func)

    fmapped = []
    for m in c.maps:
        fmapped.append(dict(func(k, v) for k, v in c.items()))
    return ChainMap(fmapped)


@fmap_for(defaultdict)
def _fmap_default_dict(func, d):
    if func.__code__.co_argcount == 1:
        func = on_values(func)

    fmapped = (func(k, v) for k, v in d.items())
    new_d = defaultdict(d.default_factory)
    new_d.update(fmapped)
    return new_d
