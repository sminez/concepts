# Concepts
### LISP and Haskell inspired functional programming concepts for Python

Originally this was called **fmap** and was only an implementation of the `fmap` function for Python3. Now that I've been tinkering around some more I thought it'd be nice to collect a few things together. (For about a day it was then called `PythFun` but then I saw the error of my ways...)

- [fmap](fmap_README.md): apply a function to all elements of a collection style object.
- [pattern_match](pattern_match_README.md): A hybrid of Haskell's pattern matching and Clojure's destructuring.
- [dispatch](pythfun/dispatch.py): single and multiple dispatch for your Python functions.

Any suggestions for improvements are welcome and if you'd like to hack away and submit a pull request for a feature then raise an issue and let me know!

I hope you enjoy!


#### NOTE:
At the moment, there are no tests for this code and it has only been run on linux under cPython 3.5. (I really should fix that...)
