from distutils.util import strtobool
from functools import partial
import json

class pipeline(object):
    def __init__(self):
        self._pipeline = []

    def add(self, checker, onFail='pass'):
        self._pipeline.append((checker, onFail))

    def addEnum(self, policy, default=None, onFail='pass'):
        checker = partial(enumCheck, policy=policy, default=default)
        self.add(checker, onFail=onFail)

    def addType(self, policy, default=None, onFail='pass'):
        checker = partial(typeCheck, policy=policy, default=default)
        self.add(checker, onFail=onFail)

    def addMakeUpper(self, policy):
        self.add(toUpper)

    def addMakeLower(self, policy):
        self.add(toLower)

    async def _processDict(self, data):
        for pi in self._pipeline:
            c, of = pi
            try:
                data = await c(data)
            except:
                data = {'pass': data, 'erase': None }.get(of)
        return data

    async def process(self, data):
        if type(data) is list:
            nl = []
            for l in list:
                nd = await self._processDict(l)
                nl.append(nd)
            return nl
        else:
            return await self._processDict(data)



def _extract2Tuple(t):
    try:
        p, d = t
    except TypeError:
        p, d = (t, None)
    except ValueError:
        p, d = (t[0], None)
    return p, d

async def _processDict(data, checkFunc, policy=None, default=None):
    if policy is None:
        return data
    retd = {}
    for k, v in data.items():
        if k in policy:
            p, d = _extract2Tuple(policy[k])
            retd[k] = await checkFunc(v, p, d, default)
        else:
            retd[k] = v
    return retd


async def _checkType(value, policy, default, globalDefault):
    if type(value) == policy:
        return value
    try:
        if type(policy) is bool:
            # Handle strings more intelligently than bool(v) does
            return policy(strtobool(value))
        return policy(value)
    except ValueError:
        if default is not None:
            return default
        elif globalDefault is not None:
            return globalDefault
        else:
            raise

async def _checkEnum(value, policy, default, globalDefault):
    if value not in policy:
        if default is not None:
            return default
        elif globalDefault is not None:
            return globalDefault
        else:
            raise ValueError(f'Value \'{value}\' not found within enumerated values [{policy}]')
    else:
        return value

async def checkType(data, policy=None, default=None):
    '''
    Convert dictionary values to prefered type as specified in the policy dictionary

    The policy dictionary must include a key for every key in the data dictionary
    that needs to be converted.  The value of this key can either be a type object
    (e.g. int, float, str) or a 2-tuple composed of a type object and a default value.
    For each key in policy that matches a key in data, a conversion attempt will
    be made if necessary.  If the attempt succeeds, the converted value will replace
    the original value in data.  If the attempt fails and a default value was provided,
    the default value will replace the original value.  Otherwise a ValueError will
    be raised.

    :param data: The dictionary that will have its values converted
    :type data: dict
    :param policy: The dictionary of policy values with each key representing a
      key to convert within the data object and each value either the type to
      convert to or a tuple containing the type plus a default value to use if
      conversion fails
    :type policy: dict
    :param default: A value of last resort to be used if a conversion fails and
    no default was provided
    :type default: any object
    :retval: Converted dictionary
    :rtype: dict
    :raises ValueError: if conversion fails and no default was provided

    ..note::
      Sample policy
      { 'state': ('str', 'stop'),
        'volume': ('int', 0)
      }
    '''
    return await _processDict(data, _checkType, policy, default)


async def checkEnum(data, policy=None, default=None):
    '''
    Check that enumerated values are correct

    The policy dictionary must include a key for every key in the data dictionary
    that needs to be checked.  The value of this key can either be a list of
    acceptable values or a 2-tuple composed of a list of acceptable values and
    a default value to be used when a match does not occur.  If no default value
    is provided and an acceptable value is not found, a ValueError will be raised

    :param data: The data dictionary that will have its values checked
    :type data: dict
    :param policy: The dictionary of policy values with each key representing a
      key to check within the data object and each value either a list of valid
      values or a tuple containing the list plus a default value to use if
      no acceptable value was found.
    :type policy: dict
    :param default: A value of last resort to be used if an acceptable value
      was not found and no default was provided within the policy
    :type default: any object
    :retval: Converted dictionary
    :rtype: dict
    :raises ValueError: if conversion fails and no default was provided

    ..note::
      Sample policy
      { 'state': (['stop', 'pause', 'play', 'starting'], 'stop') }
    '''
    return await _processDict(data, _checkEnum, policy, default)


async def makeLower(data, policy=None):
    '''
    Converts any values in dictionary to lowercase if they are strings

    :param data: The dictionary that will have its string values converted
    :type data: dict
    :retval: Converted dictionary
    :rtype: dict
    '''
    if policy is not None:
        return {k:(v.lower() if type(v) is str and k in policy else v) for (k, v) in data.items()}
    else:
        return {k:(v.lower() if type(v) is str else v) for (k, v) in data.items()}


async def makeUpper(data, policy=None):
    '''
    Converts any values in dictionary to lowercase if they are strings

    :param data: The dictionary that will have its string values converted
    :type data: dict
    :retval: Converted dictionary
    :rtype: dict
    '''

    if policy is not None:
        return {k:(v.upper() if type(v) is str and k in policy else v) for (k, v) in data.items() }
    else:
        return {k:(v.upper() if type(v) is str else v) for (k, v) in data.items() }


async def makeKeyLower(data, policy=None):
    '''
    Converts any keys in dictionary to lowercase if they are strings

    :param data: The dictionary that will have its keys converted
    :type data: dict
    :retval: Converted dictionary
    :rtype: dict
    '''
    if policy is not None:
        return {(k.lower() if type(k) is str and k in policy else k):v for (k, v) in data.items() }
    else:
        return {(k.lower() if type(k) is str else k):v for (k, v) in data.items() }


async def makeKeyUpper(data, policy=None):
    '''
    Converts any keys in dictionary to lowercase if they are strings

    :param data: The dictionary that will have its keys converted
    :type data: dict
    :retval: Converted dictionary
    :rtype: dict
    '''

    if policy is not None:
        return {(k.upper() if type(k) is str and k in policy else k):v for (k, v) in data.items() }
    else:
        return {(k.upper() if type(k) is str else k):v for (k, v) in data.items() }

async def genericOp(value, policy, default, globalDefault):
    try:
        return value.__getattribute__(policy)()
    except (AttributeError, ValueError, TypeError):
        if default is not None:
            return default
        if globalDefault is not None:
            return globalDefault
        raise

'''
    # Define data pipelines
    def _setupPipelines(self):

        def pushState():
            p = pipeline()
            p.addMakeLower(['status'])
            p.addEnum(
                { 'status': (['play', 'stop', 'pause'], 'stop')}
            )
            p.addType(
                {
                    ('status': str, 'stop'),
                    ('position': int, 0),
                    ('title': str, ''),
                    ('artist': str, ''),
                    ('album': str, ''),
                    ('albumart': str, ''),
                    ('uri': str, ''),
                    ('trackType': str, ''),
                    ('seek': int, 0),
                    ('duration': int, 0),
                    ('random': bool, False),
                    ('repeat': bool, False),
                    ('repeatSingle': bool, False),
                    ('volume': int, 0),
                    ('mute': bool, False)
                    ('stream': bool, False),
                    ('updatedb': bool, False),
                    ('volatile': bool, False),
                    ('service': str, '')
                }, default=''
            )
            return p

        def pushQueue():
            p = pipeline()
            p.addType(
                {
                    'uri': str,
                    'title': str,
                    'service': str,
                    'name': str,
                    'artist': str,
                    'album': str,
                    'type':, str,
                    'albumart': str,
                    'samplerate': str,
                    'bitdepth': str,
                    'trackType': str,
                    'channels': int,
                    'duration': int
                }
            )
'''

ti = {'state': 'play', 'volume': 50}
ti2 = {'state': 'notgood', 'volume': 50}
ti3 = {'state': 'play', 'volume': '50' }
ti4 = {'state': 'Stop', 'volume': 23 }
ti5 = {'state': 'play', 'volume': 50, 'repeat': True }

async def test(data):

    p = pipeline()
    p.add(makeLower)
    p.add(partial(checkEnum, policy={'state': (['play', 'stop', 'pause'], 'stop')}))
    p.add(partial(checkType, policy={'state': str, 'volume': int }))
    result = await p.process(data)
    print(json.dumps(result, indent=4))
