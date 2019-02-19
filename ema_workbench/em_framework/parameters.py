'''parameters and collections of parameters'''
from __future__ import (unicode_literals, print_function, absolute_import,
                        division)

import abc
import itertools
import numbers
import pandas
import six
import warnings
from scipy import stats

from .util import (NamedObject, Variable, NamedObjectMap, Counter,
                   NamedDict, combine)
from ..util import get_module_logger

# Created on Jul 14, 2016
#
# .. codeauthor::jhkwakkel <j.h.kwakkel (at) tudelft (dot) nl>

__all__ = [
    'Parameter',
    'RealParameter',
    'IntegerParameter',
    'BooleanParameter',
    'CategoricalParameter',
    'create_parameters',
    'experiment_generator']
_logger = get_module_logger(__name__)


class Constant(NamedObject):
    '''Constant class,

    can be used for any parameter that has to be set to a fixed value

    '''

    def __init__(self, name, value):
        super(Constant, self).__init__(name)
        self.value = value

    def __repr__(self, *args, **kwargs):
        return '{}(\'{}\', {})'.format(self.__class__.__name__,
                                       self.name, self.value)


class Category(Constant):
    def __init__(self, name, value):
        super(Category, self).__init__(name, value)


def create_category(cat):
    if isinstance(cat, Category):
        return cat
    else:
        return Category(str(cat), cat)


class Parameter(Variable):
    ''' Base class for any model input parameter

    Parameters
    ----------
    name : str
    lower_bound : int or float
    upper_bound : int or float
    resolution : collection
    pff : bool
          if true, sample over this parameter using resolution in case of
          partial factorial sampling

    Raises
    ------
    ValueError
        if lower bound is larger than upper bound
    ValueError
        if entries in resolution are outside range of lower_bound and
        upper_bound

    '''

    __metaclass__ = abc.ABCMeta

    INTEGER = 'integer'
    UNIFORM = 'uniform'

    def __init__(self, name, lower_bound, upper_bound, resolution=None,
                 default=None, variable_name=None, pff=False, dist=None):
        super(Parameter, self).__init__(name)

        if resolution is None:
            resolution = []

        for entry in resolution:
            if not ((entry >= lower_bound) and (entry <= upper_bound)):
                raise ValueError(('resolution not consistent with lower and '
                                  'upper bound'))

        if lower_bound >= upper_bound:
            raise ValueError('upper bound should be larger than lower bound')

        self.resolution = resolution
        self.default = default
        self.variable_name = variable_name
        self.pff = pff
        self.rv_gen = dist

    @property
    def lower_bound(self):
        return _get_lower_bound_from_dist(self.rv_gen)

    @property
    def upper_bound(self):
        return _get_upper_bound_from_dist(self.rv_gen)


    def __eq__(self, other):
        comparison = [all(hasattr(self, key) == hasattr(other, key) and
                          getattr(self, key) == getattr(other, key) for key
                          in self.__dict__.keys() if key != 'rv_gen')]
        comparison.append(self.__class__ == other.__class__)
        if self.rv_gen is None and other.rv_gen is not None:
            return False
        if self.rv_gen is not None and other.rv_gen is None:
            return False
        if self.rv_gen is not None and other.rv_gen is not None:
            comparison.append(self.rv_gen.args == other.rv_gen.args)
            comparison.append(self.rv_gen.kwds == other.rv_gen.kwds)
            comparison.append(self.rv_gen.a == other.rv_gen.a)
            comparison.append(self.rv_gen.b == other.rv_gen.b)
            comparison.append(self.rv_gen.dist.name == other.rv_gen.dist.name)
        return all(comparison)

    def __str__(self):
        return self.name

    def __repr__(self, *args, **kwargs):
        start = '{}(\'{}\', {}, {}'.format(self.__class__.__name__,
                                           self.name,
                                           self.lower_bound, self.upper_bound)

        if self.resolution:
            start += ', resolution={}'.format(self.resolution)
        if self.default:
            start += ', default={}'.format(self.default)
        if self.variable_name != [self.name]:
            start += ', variable_name={}'.format(self.variable_name)
        if self.pff:
            start += ', pff={}'.format(self.pff)

        start += ')'

        return start


def _get_bounds_from_dist(dist):
    ppf_zero = 0
    try:
        if isinstance(dist.dist, stats.rv_discrete):
            # ppf at actual zero for rv_discrete gives lower bound - 1
            # due to a quirk in the scipy.stats implementation
            # so we use the smallest positive float instead
            ppf_zero = 5e-324
    except AttributeError:
        pass
    lower_bound = dist.ppf(ppf_zero)
    upper_bound = dist.ppf(1.0)
    return lower_bound, upper_bound

def _get_lower_bound_from_dist(dist):
    ppf_zero = 0
    try:
        if isinstance(dist.dist, stats.rv_discrete):
            # ppf at actual zero for rv_discrete gives lower bound - 1
            # due to a quirk in the scipy.stats implementation
            # so we use the smallest positive float instead
            ppf_zero = 5e-324
    except AttributeError:
        pass
    lower_bound = dist.ppf(ppf_zero)
    return lower_bound

def _get_upper_bound_from_dist(dist):
    upper_bound = dist.ppf(1.0)
    return upper_bound


class RealParameter(Parameter):
    ''' real valued model input parameter

    Parameters
    ----------
    name : str
    lower_bound : int or float
    upper_bound : int or float
    resolution : iterable
    variable_name : str, or list of str

    Raises
    ------
    ValueError
        if lower bound is larger than upper bound
    ValueError
        if entries in resolution are outside range of lower_bound and
        upper_bound

    '''

    def __init__(self, name, lower_bound=None, upper_bound=None, resolution=None,
                 default=None, variable_name=None, pff=False, dist=None):

        if dist is None and (lower_bound is None or upper_bound is None):
            raise ValueError("must give lower_bound and upper_bound, or dist")

        if dist is None:
            from scipy.stats import uniform
            dist = uniform(lower_bound, upper_bound-lower_bound)
        else:
            lower_bound, upper_bound = _get_bounds_from_dist(dist)

        super(
            RealParameter,
            self).__init__(
            name,
            lower_bound,
            upper_bound,
            resolution=resolution,
            default=default,
            variable_name=variable_name,
            pff=pff,
            dist=dist
        )


    def __eq__(self, other):
        comparison = [all(hasattr(self, key) == hasattr(other, key) and
                          getattr(self, key) == getattr(other, key) for key
                          in self.__dict__.keys() if key != 'rv_gen')]
        comparison.append(self.__class__ == other.__class__)
        comparison.append(self.rv_gen.args == other.rv_gen.args)
        comparison.append(self.rv_gen.kwds == other.rv_gen.kwds)
        comparison.append(self.rv_gen.a == other.rv_gen.a)
        comparison.append(self.rv_gen.b == other.rv_gen.b)
        comparison.append(self.rv_gen.dist.name == other.rv_gen.dist.name)
        return all(comparison)

    def __repr__(self, *args, **kwargs):
        start = '{}(\'{}\', {}, {}'.format(self.__class__.__name__,
                                           self.name,
                                           self.lower_bound, self.upper_bound)

        if self.resolution:
            start += ', resolution={}'.format(self.resolution)
        if self.default:
            start += ', default={}'.format(self.default)
        if self.variable_name != [self.name]:
            start += ', variable_name={}'.format(self.variable_name)
        if self.pff:
            start += ', pff={}'.format(self.pff)
        try:
            dist_name = self.rv_gen.dist.name
        except:
            pass
        else:
            if dist_name != 'uniform':
                start += ', dist={}'.format(dist_name)

        start += ')'

        return start


class IntegerParameter(Parameter):
    ''' integer valued model input parameter

    Parameters
    ----------
    name : str
    lower_bound : int
    upper_bound : int
    resolution : iterable
    variable_name : str, or list of str

    Raises
    ------
    ValueError
        if lower bound is larger than upper bound
    ValueError
        if entries in resolution are outside range of lower_bound and
        upper_bound, or not an numbers.Integral instance
    ValueError
        if lower_bound or upper_bound is not an numbers.Integral instance

    '''

    def __init__(self, name, lower_bound=None, upper_bound=None, resolution=None,
                 default=None, variable_name=None, pff=False, dist=None):

        if dist is None and (lower_bound is None or upper_bound is None):
            raise ValueError("must give lower_bound and upper_bound, or dist")

        if dist is None:
            from scipy.stats import randint
            dist = randint(lower_bound, upper_bound+1)
        else:
            lower_bound, upper_bound = _get_bounds_from_dist(dist)
            if lower_bound != int(lower_bound):
                raise TypeError('lower bound is not an integer')
            lower_bound = int(lower_bound)
            if upper_bound != int(upper_bound):
                raise TypeError('upper bound is not an integer')
            upper_bound = int(upper_bound)

        super(
            IntegerParameter,
            self).__init__(
            name,
            lower_bound,
            upper_bound,
            resolution=resolution,
            default=default,
            variable_name=variable_name,
            pff=pff,
            dist=dist)

        lb_int = isinstance(lower_bound, numbers.Integral)
        up_int = isinstance(upper_bound, numbers.Integral)

        if not (lb_int or up_int):
            raise ValueError('lower bound and upper bound must be integers')

        for entry in self.resolution:
            if not isinstance(entry, numbers.Integral):
                raise ValueError(('all entries in resolution should be '
                                  'integers'))


    def __eq__(self, other):
        comparison = [all(hasattr(self, key) == hasattr(other, key) and
                          getattr(self, key) == getattr(other, key) for key
                          in self.__dict__.keys() if key != 'rv_gen')]
        comparison.append(self.__class__ == other.__class__)
        comparison.append(self.rv_gen.args == other.rv_gen.args)
        comparison.append(self.rv_gen.kwds == other.rv_gen.kwds)
        comparison.append(self.rv_gen.a == other.rv_gen.a)
        comparison.append(self.rv_gen.b == other.rv_gen.b)
        comparison.append(self.rv_gen.dist.name == other.rv_gen.dist.name)
        return all(comparison)



class CategoricalParameter(IntegerParameter):
    ''' categorical model input parameter

    Parameters
    ----------
    name : str
    categories : collection of obj
    variable_name : str, or list of str
    multivalue : boolean
                 if categories have a set of values, for each variable_name
                 a different one.

    '''

    @property
    def categories(self):
        return self._categories

    @categories.setter
    def categories(self, values):
        self._categories.extend(values)

    def __init__(self, name, categories, default=None, variable_name=None,
                 pff=False, multivalue=False):
        lower_bound = 0
        upper_bound = len(categories) - 1

        if upper_bound == 0:
            raise ValueError('there should be more than 1 category')

        super(
            CategoricalParameter,
            self).__init__(
            name,
            lower_bound,
            upper_bound,
            resolution=None,
            default=default,
            variable_name=variable_name,
            pff=pff,
            dist=None)
        cats = [create_category(cat) for cat in categories]

        self._categories = NamedObjectMap(Category)

        self.categories = cats
        self.resolution = [i for i in range(len(self.categories))]
        self.multivalue = multivalue

    def index_for_cat(self, category):
        '''return index of category

        Parameters
        ----------
        category : object

        Returns
        -------
        int


        '''
        for i, cat in enumerate(self.categories):
            if cat.name == category:
                return i
        raise ValueError("category not found")

    def cat_for_index(self, index):
        '''return category given index

        Parameters
        ----------
        index  : int

        Returns
        -------
        object

        '''

        return self.categories[index]

    def invert(self, name):
        ''' invert a category to an integer

        Parameters
        ----------
        name : obj
               category

        Raises
        ------
        ValueError
            if category is not found

        '''
        warnings.warn('deprecated, use index_for_cat instead')
        return self.index_for_cat(name)

    def __repr__(self, *args, **kwargs):
        template1 = 'CategoricalParameter(\'{}\', {}, default={})'
        template2 = 'CategoricalParameter(\'{}\', {})'

        if self.default:
            representation = template1.format(self.name, self.resolution,
                                              self.default)
        else:
            representation = template2.format(self.name, self.resolution)

        return representation


class BinaryParameter(CategoricalParameter):
    ''' a categorical model input parameter that is only True or False

    Parameters
    ----------
    name : str
    '''

    def __init__(self, name, default=None, ):
        super(
            BinaryParameter,
            self).__init__(
            name,
            categories=[
                False,
                True],
            default=default)


class BooleanParameter(IntegerParameter):
    ''' boolean model input parameter

    A BooleanParameter is similar to a CategoricalParameter, except
    the category values can only be True or False.

    Parameters
    ----------
    name : str
    variable_name : str, or list of str

    '''

    def __init__(self, name, default=None, variable_name=None,
                 pff=False, dist=None):
        if dist is not None:
            lower_bound, upper_bound = _get_bounds_from_dist(dist)
            if lower_bound != 0 or upper_bound != 1:
                raise ValueError('a bool distribution must have unit range')

        super(BooleanParameter, self).__init__(
            name, 0, 1, resolution=None, default=default,
            variable_name=variable_name, pff=pff, dist=dist)

        self.categories = [False, True]
        self.resolution = [0, 1]

    def __repr__(self, *args, **kwargs):
        template1 = 'BooleanParameter(\'{}\', default={})'
        template2 = 'BooleanParameter(\'{}\', )'

        if self.default:
            representation = template1.format(self.name,
                                              self.default)
        else:
            representation = template2.format(self.name, )

        return representation


class Policy(NamedDict):
    # TODO:: separate id and name
    # if name is not provided fall back on id
    # id will always be a number and can be generated by
    # a counter
    # the new experiment class can than take the names from
    # policy and scenario to create a unique name while also
    # multiplying the ID's (assuming we count from 1 onward) to get
    # a unique experiment ID
    id_counter = Counter(1)

    def __init__(self, name, **kwargs):
        super(Policy, self).__init__(name, **kwargs)
        self.id = Policy.id_counter()

    def to_list(self, parameters):
        '''get list like representation of policy where the
        parameters are in the order of levers'''

        return [self[param.name] for param in parameters]

    def __repr__(self):
        return "Policy({})".format(super(Policy, self).__repr__())


class Scenario(NamedDict):
    # we need to start from 1 so scenario id is known
    id_counter = Counter(1)

    def __init__(self, name=Counter(), **kwargs):
        super(Scenario, self).__init__(name, **kwargs)
        self.id = Scenario.id_counter()

    def __repr__(self):
        return "Scenario({})".format(super(Scenario, self).__repr__())


class Case(NamedObject):
    '''A convenience object that contains a specification
    of the model, policy, and scenario to run

    TODO:: we need a better name for this. probably this should be
    named Experiment, while Experiment should be
    ExperimentReplication

    '''

    def __init__(self, name, model_name, policy, scenario, experiment_id):
        super(Case, self).__init__(name)
        self.experiment_id = experiment_id
        self.policy = policy
        self.model_name = model_name
        self.scenario = scenario


class Experiment(NamedDict):
    '''helper class that combines scenario, policy, any constants, and
    replication information (seed etc) into a single dictionary.

    '''

    def __init__(self, scenario, policy, constants, replication=None):
        scenario_id = scenario.id
        policy_id = policy.id

        if replication is None:
            replication_id = 1
        else:
            replication_id = replication.id
            constants = combine(constants, replication)

        # this is a unique identifier for an experiment
        # we might also create a better looking name
        self.id = scenario_id * policy_id * replication_id
        name = '{}_{}_{}'.format(scenario.name, policy.name, replication_id)

        super(Experiment, self).__init__(
            name, **combine(scenario, policy, constants))


def experiment_generator(scenarios, model_structures, policies, zip_over=None):
    '''

    generator function which yields experiments

    Parameters
    ----------
    designs : iterable of dicts
    model_structures : list
    policies : list
    zip_over : Collection[str], optional
        A collection that contains exactly two or three members of the set
        {'scenarios', 'policies', 'models'}.  If a set is given, the length
        of all other arguments that are indicated in this set must be the
        same, and the experiment generator will create experiments based on
        a `zip` through the values in these collections, instead of creating
        experiments across all possible combinations of the values.

    Notes
    -----
    When called with zip_over as None, this generator is essentially
    three nested loops: for each model structure,
    for each policy, for each scenario, return the experiment. This means
    that designs should not be a generator because this will be exhausted after
    the running the first policy on the first model.  If zip_over contains
    two items, then those two will be paired up, but there will still be
    two nested loops.

    '''
    if zip_over is None:
        zip_over = set()
    else:
        zip_over = set(zip_over)

    if not zip_over.issubset({'scenarios', 'policies', 'models'}):
        raise ValueError("zip_over must be subset of {'scenarios', 'policies', 'models'} or None")
    if len(zip_over) == 1:
        raise ValueError("zip_over cannot be one item")

    if zip_over == {'scenarios', 'policies', 'models'}:
        assert len(model_structures) == len(policies)
        assert len(model_structures) == len(scenarios)
        jobs = (
            (m_, p_, s_)
            for m_, p_, s_ in zip(
                model_structures, policies, scenarios
            )
        )
    elif zip_over == {'scenarios', 'policies'}:
        assert len(scenarios) == len(policies)
        jobs = (
            (m_, p_, s_)
            for m_, (p_, s_) in itertools.product(
                model_structures, zip(policies, scenarios)
            )
        )
    elif zip_over == {'scenarios', 'models'}:
        assert len(model_structures) == len(scenarios)
        jobs = (
            (m_, p_, s_)
            for p_, (m_, s_) in itertools.product(
                policies, zip(model_structures, scenarios)
            )
        )
    elif zip_over == {'policies', 'models'}:
        assert len(model_structures) == len(policies)
        jobs = (
            (m_, p_, s_)
            for s_, (m_, p_) in itertools.product(
                scenarios, zip(model_structures, policies)
            )
        )
    else:
        jobs = itertools.product(model_structures, policies, scenarios)

    for i, job in enumerate(jobs):
        msi, policy, scenario = job
        name = '{} {} {}'.format(msi.name, policy.name, i)
        case = Case(name, msi.name, policy, scenario, i)
        yield case


def parameters_to_csv(parameters, file_name):
    '''Helper function for writing a collection of parameters to a csv file

    Parameters
    ----------
    parameters : collection of Parameter instances
    file_name :  str


    The function iterates over the collection and turns these into a data
    frame prior to storing them. The resulting csv can be loaded using the
    create_parameters function. Note that currently we don't store resolution
    and default attributes.

    '''

    params = {}

    for i, param in enumerate(parameters):

        if isinstance(param, CategoricalParameter):
            values = param.resolution
        else:
            values = param.lower_bound, param.upper_bound

        dict_repr = {j: value for j, value in enumerate(values)}
        dict_repr['name'] = param.name

        params[i] = dict_repr

    params = pandas.DataFrame.from_dict(params, orient='index')

    # for readability it is nice if name is the first column, so let's
    # ensure this
    cols = params.columns.tolist()
    cols.insert(0, cols.pop(cols.index('name')))
    params = params.reindex(columns=cols)

    # we can now safely write the dataframe to a csv
    pandas.DataFrame.to_csv(params, file_name, index=False)


def create_parameters(uncertainties, **kwargs):
    '''Helper function for creating many Parameters based on a DataFrame
    or csv file

    Parameters
    ----------
    uncertainties : str, DataFrame
    **kwargs : dict, arguments to pass to pandas.read_csv

    Returns
    -------
    list of Parameter instances


    This helper function creates uncertainties. It assumes that the
    DataFrame or csv file has a column titled 'name', optionally a type column
    {int, real, cat}, can be included as well. the remainder of the columns
    are handled as values for the parameters. If type is not specified,
    the function will try to infer type from the values.

    Note that this function does not support the resolution and default kwargs
    on parameters.

    An example of a csv:

    NAME,TYPE,,,
    a_real,real,0,1.1,
    an_int,int,1,9,
    a_categorical,cat,a,b,c

    this CSV file would result in

    [RealParameter('a_real', 0, 1.1, resolution=[], default=None),
     IntegerParameter('an_int', 1, 9, resolution=[], default=None),
     CategoricalParameter('a_categorical', ['a', 'b', 'c'], default=None)]

    '''

    if isinstance(uncertainties, six.string_types):
        uncertainties = pandas.read_csv(uncertainties, **kwargs)
    elif not isinstance(uncertainties, pandas.DataFrame):
        uncertainties = pandas.DataFrame.from_dict(uncertainties)
    else:
        uncertainties = uncertainties.copy()

    parameter_map = {'int': IntegerParameter,
                     'real': RealParameter,
                     'cat': CategoricalParameter,
                     'bool': BooleanParameter,
                     }

    # check if names column is there
    if ('NAME' not in uncertainties) and ('name' not in uncertainties):
        raise IndexError('name column missing')
    elif ('NAME' in uncertainties.columns):
        names = uncertainties.ix[:, 'NAME']
        uncertainties.drop(['NAME'], axis=1, inplace=True)
    else:
        names = uncertainties.ix[:, 'name']
        uncertainties.drop(['name'], axis=1, inplace=True)

    # check if type column is there
    infer_type = False
    if ('TYPE' not in uncertainties) and ('type' not in uncertainties):
        infer_type = True
    elif ('TYPE' in uncertainties):
        types = uncertainties.ix[:, 'TYPE']
        uncertainties.drop(['TYPE'], axis=1, inplace=True)
    else:
        types = uncertainties.ix[:, 'type']
        uncertainties.drop(['type'], axis=1, inplace=True)

    uncs = []
    for i, row in uncertainties.iterrows():
        name = names[i]
        values = row.values[row.notnull().values]
        type = None  # @ReservedAssignment

        if infer_type:
            if len(values) != 2:
                type = 'cat'  # @ReservedAssignment
            else:
                l, u = values

                if isinstance(
                        l, numbers.Integral) and isinstance(
                        u, numbers.Integral):
                    type = 'int'  # @ReservedAssignment
                else:
                    type = 'real'  # @ReservedAssignment

        else:
            type = types[i]  # @ReservedAssignment

            if (type != 'cat') and (len(values) != 2):
                raise ValueError(
                    'too many values specified for {}, is {}, should be 2'.format(
                        name, values.shape[0]))

        if type == 'cat':
            uncs.append(parameter_map[type](name, values))
        else:
            uncs.append(parameter_map[type](name, *values))
    return uncs
