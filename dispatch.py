'''
Adding simple single & multiple dispatch to Python.
```````````````````````````````````````````````````

Unlike functools.singledispatch, this will not work back through the MRO
to find a matching superclass. Instead it will immediately resort to the
default implementation.

NOTE:   *args and **kwargs are _not_ allowed in the signature of the
        function being defined.
'''
from functools import wraps


def dispatch_on(index=0, func=None):
    '''
    Allow the implementation of a function to vary based on the type of
    of its arguments.
    Default is single dispatch on the first argument but you can supply
    any of the following as the key for implementation lookup:
        any single index   -->  dispatch_on(1)
        a tuple of indices -->  dispatch_on((0,2))
        all arguments      -->  dispatch_on('all')

    Once the decorated function has been defined, you can use
    <original_func>.add(<types>) to register an implementation.

    NOTE: <types> must match the form of the original specification
          used in @dispatch_on.

    If no implementation is found, then the decorated function is used
    as a default.
    '''
    # A quick hack to allow using this as a decorator with arguments
    if func is None:
        return lambda f: dispatch_on(index, f)

    implementations = {}

    if index == 'all':
        multi = True
        # Horrible but correct so long as func does not use *args or **kwargs
        key_len = func.__code__.co_argcount
    elif type(index) == tuple:
        multi = True
        key_len = len(index)
    elif type(index) == int:
        multi = False
    else:
        raise ValueError("Invalid argument specification for dispatch")

    def add(key, func=None):
        '''
        Add an implementation of func for the given key. The form of key
        must match the form given for index above.
        '''
        # Same hack as before
        if func is None:
            return lambda f: add(key, f)

        if multi:
            if len(key) != key_len:
                raise TypeError(
                    'The base case takes {} parameters. ({} supplied)'.format(
                        key_len, len(key)))

        implementations[key] = func
        return func

    @wraps(func)
    def wrapped(*args, **kwargs):
        '''
        Attempt to use an implementation if there is one,
        otherwise use the default.
        '''
        if multi:
            if index == 'all':
                dispatch_key = tuple([type(a) for a in args])
            else:
                dispatch_key = tuple(type(args[i]) for i in index)
        else:
            dispatch_key = type(args[index])

        implementation = implementations.get(dispatch_key, func)
        return implementation(*args, **kwargs)

    wrapped.implementations = implementations
    wrapped.add = add
    return wrapped


def instance(func, implementation, arg_type):
    '''
    Register a function as the implementation of func for a given type.
    i.e instance(fmap, _fmap_my_type, my_type)

    This is an alternative to explicitly wrapping the function definition
    in question with @func.add(arg_type) to allow run-time registration
    and registration of pre-defined functions.
    '''
    if 'dispatch' in dir(func):
        func.add(arg_type, implementation)
    else:
        raise TypeError(
            '{} has not been decorated with `dispatch_on`.'.format(func)
        )
