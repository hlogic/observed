import unittest
import sys
import os
sys.path.insert(0, os.path.abspath('..'))
import observed
from observed import observable_function, observable_method


def get_caller_name(caller):
    """Find the name of a calling (i.e. observed) object.

    Args:
        caller: The observed object which is calling an observer.

    Returns:
        The name of the caller.
    """
    if hasattr(caller, "__self__"):
        # caller is a Foo instance
        name = caller.__self__.name
    else:
        # caller is a function.
        name = caller.__name__
    return name


def clear_list(l):
    """Remove all entries from a list.

    Args:
        l: The list to be cleared.
    """
    while True:
        try:
            l.pop(0)
        except IndexError:
            break


class Foo(object):
    """A generic class with observable methods.

    Attributes:
        name - string: A string naming the instance.
        buf - list: A buffer for collecting a record of called methods. My
            methods are set up to append a string to buf when they are called.
            The strings are formatted in one of two ways. If the method being
            called accepts the observed object as a first argument, the string
            is:
            "%s%s%s"%(self.name, method_name, caller_name)
            where method_name is the name of the method being called on me and
            caller_name is the name of the calling Foo instance or the name of
            the calling function. Note that the name of the calling instance is
            NOT the same thing as the name of the calling method, which doesn't
            exist. If the method being called does not accept the caller as a
            first argument, the string written to buf is:
            "%s%s"%(self.name, method_name).
    """

    def __init__(self, name, buf):
        """Initialize a Foo object.

        Args:
            name: A name for this instance.
            buf: A buffer (list) into which I write data when my methods are
                called. See the class docstring for details.
        """
        self.name = name
        self.buf = buf
    
    @observable_method
    def bar(self):
        self.buf.append("%sbar"%(self.name,))
    
    def baz(self):
        self.buf.append("%sbaz"%(self.name,))
    
    @observable_method
    def milton(self, caller):
        caller_name = get_caller_name(caller)
        self.buf.append("%smilton%s"%(self.name, caller_name))
    
    def waldo(self, caller):
        caller_name = get_caller_name(caller)
        self.buf.append("%swaldo%s"%(self.name, caller_name))

    def observable_methods(self):
        return [self.bar, self.milton]

    def method_info(self):
        return [(self.bar, False),
                (self.baz, False),
                (self.milton, True),
                (self.waldo, True)]


class Goo(Foo):
    """A class using the descriptor strategy for observable methods.

    I am entirely similar to Foo except that my observable methods use the
    descriptor persistence strategy. See the docstring for observable_method
    for a detailed explanation.
    """

    def bar(self):
        self.buf.append("%sbar"%(self.name,))
    bar = observable_method(bar, strategy='descriptor')

    def milton(self, caller):
        caller_name = get_caller_name(caller)
        self.buf.append("%smilton%s"%(self.name, caller_name))
    milton = observable_method(milton, strategy='descriptor')


# Not currently used

def get_observables(*objs):
    """Get a list observables from some objects.

    For each object, if it's a Foo or subclass, we get all of the object's
    observable methods. If it's a function
    """

    observables = []
    for obj in objs:
        if isinstance(obj, Foo):
            observables.extend(obj.observable_methods())
        elif isinstance(obj, observed.ObservableFunction):
            observables.append(obj)
        else:
            raise TypeError("Object of type %s not observable"%(type(obj),))
    return observables


def get_observers(*objs):
    observer_sets = []
    single_observers = []
    for obj in objs:
        if isinstance(obj, Foo):
            single_observers.extend(obj.method_info())
        else:
            single_observers.append((obj[0], obj[1]))
    for num_observers in range(len(single_observers)):
        for comb in itertools.combinations(single_observers, num_observers):
            observer_sets.append(comb)
    return observer_sets

# End not currently used


def make_observed_dict(*objects):
    """Construct a table of observable objects keyed by unique string names.

    In test scripts, it is convenient to able to iterate over combinations of
    observed and observing objects. However, we may wish to define these
    combinations before the objects are constructed. Therefore, we define the
    combinations as a set of string identifiers and then _after_ the objects
    are created we use this function to build a table of objects keyed by
    those identifiers.

    Args:
        objects: Collection of objects to be formed into the table.

    Returns:
        A table of observable objects keyed by unique string identifiers. A Foo
        instance with .name="my_foo" produces two entries in the table:
            "my_foo.bar": my_foo.bar
            "my_foo.milton": my_foo.milton
        and a function func produces one entry:
            "func": func.
    """
    result = []
    for obj in objects:
        if isinstance(obj, Foo):
            result.append((obj.name+'.bar', obj.bar))
            result.append((obj.name+'.milton', obj.milton))
        elif isinstance(obj, observed.ObservableFunction):
            result.append((obj.__name__, obj))
        else:
            raise TypeError("Object of type %s not observable"%(type(obj),))
    return dict(result)


def make_observer_dict(*objects):
    """Construct a table of observer objects keyed by unique string names.

    Take a look at the docstring for make_observed_dict. This function is
    essentially the same thing but for observers instead of observables.
    """
    result = []
    for obj in objects:
        if isinstance(obj, Foo):
            for method_name in ['bar', 'baz', 'milton', 'waldo']:
                s = obj.name+'.'+method_name
                result.append((s, getattr(obj, method_name)))
        else:
            result.append((obj.__name__, obj))
    return dict(result)


class TestBasics(unittest.TestCase):
    """Test that observers are called when the observed object is called."""

    ITEMS = [('a.bar',
              [('b.baz', False)],
              ['abar', 'bbaz'],
              ['abar']),
             ('a.bar',
              [('b.bar', False), ('b.baz', False)],
              ['abar', 'bbar', 'bbaz'],
              ['abar']),
             ('a.bar',
              [('b.bar', False), ('b.baz', False), ('f', False)],
              ['abar', 'bbar', 'bbaz', 'f'],
              ['abar']),
             ('f',
              [('b.bar', False), ('b.baz', False), ('a.bar', False)],
              ['abar', 'bbar', 'bbaz', 'f'],
              ['f']),
             ('a.bar',
              [('b.milton', True), ('b.waldo', True)],
              ['abar', 'bmiltona', 'bwaldoa'],
              ['abar']),
             ('f',
              [('b.milton', True), ('b.baz', False)],
              ['bbaz', 'bmiltonf', 'f'],
              ['f']),
             ('c.bar',
              [('a.bar', False), ('d.baz', False), ('d.waldo', True)],
              ['abar', 'cbar', 'dbaz', 'dwaldoc'],
              ['cbar'])
            ]

    def setUp(self):
        self.buf = []
    
    def tearDown(self):
        pass    

    def test_callbacks(self):
        """
        Test all combinations of types acting as observed and observer.

        For each combination of observed and observer we check that all
        observers are called. We also check that after discarding the
        observers subsequent invocations of the observed object do not call
        any observers.
        """

        for observed_str, observer_info, expected, final in self.ITEMS:
            a = Foo('a', self.buf)
            b = Foo('b', self.buf)
            c = Goo('c', self.buf)
            d = Goo('d', self.buf)
            
            @observable_function
            def f():
                self.buf.append('f')
            
            @observable_function
            def g(caller):
                self.buf.append('g%s'%(caller,))
            
            observed_objects = make_observed_dict(a, b, c, d, f)
            observer_objects = make_observer_dict(a, b, c, d, f, g)

            observed = observed_objects[observed_str]
            for observer_str, identify_observed in observer_info:
                observer = observer_objects[observer_str]
                observed.add_observer(observer,
                    identify_observed=identify_observed)
            observed()
            self.buf.sort()
            self.assertEqual(expected, self.buf)

            clear_list(self.buf)
            for observer_str, _ in observer_info:
                observer = observer_objects[observer_str]
                observed.discard_observer(observer)
            observed()
            self.assertEqual(final, self.buf)

            self.buf = []

    def test_discard(self):
        """
        discard_observer prevents future ivocation.
        """
        a = Foo('a', self.buf)
        def f():
            self.buf.append('f')
        
        a.bar.add_observer(f)
        result = a.bar.discard_observer(f)
        self.assertEqual(result, True)
        result = a.bar.discard_observer(f)
        self.assertEqual(result, False)
        a.bar()
        self.assertEqual(self.buf, ['abar'])

    def test_unbound_method(self):
        f = Foo('f', self.buf)

        def func():
            self.buf.append('func')

        f.bar.add_observer(func)
        Foo.bar(f)
        self.assertEqual(self.buf, ['fbar', 'func'])

    def test_equality(self):
        f = Foo('f', self.buf)
        g = Foo('g', self.buf)

        @observable_function
        def func():
            self.buf.append('func')

        self.assertEqual(Foo.bar, Foo.bar)
        self.assertEqual(f.bar, f.bar)
        self.assertNotEqual(f.bar, g.bar)
        self.assertEqual(func, func)

    def test_callerIdentification(self):
        """
        The observed object can pass itself as first argument.
        """
        a = Foo('a', self.buf)
        
        @observable_function
        def f():
            self.buf.append('f')
        
        def g(caller):
            self.buf.append('g%s'%(caller.__name__,))
        
        f.add_observer(g, identify_observed=True)
        f.add_observer(a.milton, identify_observed=True)
        f()
        self.buf.sort()
        self.assertEqual(self.buf, ['amiltonf','f', 'gf'])


if __name__ == "__main__":
    unittest.main()
