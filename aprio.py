#!/usr/bin/env python
#
# aprio is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# aprio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with aprio.  If not, see <http://www.gnu.org/licenses/>.
""" aprio stands for "Automatic Priority"
"""

import os
import logging, logging.config
import math
import time
from datetime import timedelta
from pprint import pprint


try:
    import psutil
except ImportError:
    print("psutil module not found!")
    exit(1)

try:
    import daemon
except ImportError:
    print("daemon module not found!")
    exit(1)


try:
    import argparse
except ImportError:
    print("argparse module not found!")
    exit(1)


class Transpire(object):
    """Supply common time constants
    """
    def __init__(self):
        self.second = timedelta(seconds=1).total_seconds()
        self.minute = timedelta(minutes=1).total_seconds()
        self.hour = timedelta(hours=1).total_seconds()
        self.day = timedelta(days=1).total_seconds()
        self.week = timedelta(weeks=1).total_seconds()
        self.month = timedelta(weeks=4).total_seconds()


ELAPSED = Transpire()
CONFIG = {}
CONFIG['LOAD_THRESHOLD'] = psutil.cpu_count() / 2
if CONFIG['LOAD_THRESHOLD'] < 1:
    CONFIG['LOAD_THRESHOLD'] = psutil.cpu_count()
CONFIG['CPU_THRESHOLD'] = 50.0
CONFIG['CPUTIME_THRESHOLD'] = '30m'
CONFIG['TIME_SCALE'] = '1w'
CONFIG['POLL'] = 3
CONFIG['TEST_MODE'] = False
CONFIG['VERBOSE'] = False
CONFIG['QUIET'] = False

def time_scale_convert(scale_fmt):
    """Converts simple string format to POSIX time
    
    scale_fmt -- Accepts a float+character format string
        Example:
            '1.5y' == 1 year, six months
            '30s' == 30 seconds
    """
    logger = logging.getLogger(__name__)
    if not isinstance(scale_fmt, str):
        raise TypeError("Invalid time scale (expecting 'str'): {0}"
            .format(type(scale_fmt)))
    
    if len(scale_fmt) < 2:
        raise ValueError("Invalid format: '{0}'"
            .format(scale_fmt))
    
    _modifiers = [[
        's','m','h',
        'd','w','M',
        'y'
    ],
    [
        ELAPSED.second, ELAPSED.minute, ELAPSED.hour,
        ELAPSED.day, ELAPSED.week, ELAPSED.month, ELAPSED.month*12
    ]]
    _digits = [ str(x) for x in range(10) ]
    _digits.append('.')
    
    modifiers = dict(zip(*_modifiers))    
    scale = scale_fmt[-1]
    factor = scale_fmt[0:-1]
    
    decimals = 0
    for char in factor:
        if char is '.':
            decimals += 1
        if char not in _digits or decimals > 1:
            raise ValueError("Invalid time factor: {0}".format(scale_fmt))
        
    if scale not in modifiers.keys():
        raise ValueError("Invalid time scale modifier: {0}".format(scale))
    
    return float(factor) * modifiers[scale]

def renice(proc, nice_value=0):
    """Change the process priority of a psutil.Process object
    """
    logger = logging.getLogger(__name__)
    nice_current = 255
    try:
        pid = proc.pid
        nice_previous = proc.get_nice()
        
        if nice_previous < 0:
            return

        if nice_value <= nice_previous:
            return

        if not CONFIG['TEST_MODE']:
            proc.set_nice(nice_value)

        if not CONFIG['TEST_MODE']:
            nice_current = proc.get_nice()
        else:
            nice_current = nice_value

        logger.info("{0}:Priority modified ({1} -> {2})"
            .format(pid, nice_previous, nice_current))
    except psutil.AccessDenied:
        logger.warning("{0}:{1}:Permission denied setting nice to {2}"
            .format(pid, proc.username(), nice_value))
    except psutil.NoSuchProcess:
        return
    return nice_current


def convert_nice(proc, **kwargs):
    """Analyzes a process' total kernel time, or the time since the process
    began.  If the time meets or exceeds a defined threshold, an
    appropriate nice value will be applied to the process.

    Keyword Arguments:
    model -- (default 'relative')
        'kernel' = Total CPU time accumulated
        'relative' = Total time elapsed since process started
    nice_min -- (default 0)
    nice_max -- (default 20)
    time_scale -- (default 1 month)
    """
    logger = logging.getLogger(__name__)
    model = 'relative'
    nice_min = 0
    nice_max = 20
    time_scale = ELAPSED.month
    total_time = 0
    
    if kwargs.has_key('model'):
        model = kwargs['model']
    
    if kwargs.has_key('nice_min'):
        nice_min = kwargs['nice_min']
        
    if kwargs.has_key('nice_max'):
        nice_max = kwargs['nice_max']
        
    if kwargs.has_key('time_scale'):
        time_scale = kwargs['time_scale']
    
    if model == 'kernel':
        time_user, time_system = proc.get_cpu_times()  
        total_time = time_user + time_system
    elif model == 'relative':
        total_time = time.time() - proc.create_time()
    else:
        raise ValueError('"{0}" is not a valid time model'.format(model))
        
    nice = 0
    try:
        nice = nice_min - total_time * (-nice_max / (time_scale + 1))
        if nice > nice_max:
            nice = nice_max
    except ZeroDivisionError:
        return int(nice_max)
    finally:
        return int(math.floor(nice))
    
    return nice 


def filter_processes(cpu_threshold=CONFIG['CPU_THRESHOLD'],
                    cputime_threshold=CONFIG['CPUTIME_THRESHOLD'],
                    **kwargs):
    """Yield a filtered process list matching system usage criteria.
    
    Keyword ARGUMENTS:
    cpu_threshold -- must exceed CPU% (default 50.0)
    cputime_threshold -- must exceed CPU TIME in seconds (default 1.0)
    user -- yield processes owned by a particular account
    """
    logger = logging.getLogger(__name__)
    user = ""
    if kwargs.has_key('user'):
        user = kwargs['user']

    for proc in psutil.process_iter():
        try:
            pid = proc.pid
            username = proc.username()
            user_time, system_time = proc.cpu_times()
            cputime_total = user_time + system_time
            uid, euid, _ = proc.uids()

            if uid == 0 or euid == 0:
                continue

            if pid == os.getpid():
                continue

            cpu = proc.get_cpu_percent(interval=0.05)
            if cpu > cpu_threshold:
                if cputime_total > cputime_threshold:
                    if user:
                        if user != username:
                            continue
                    yield proc

        except psutil.NoSuchProcess as ex:
            logger.debug("{0}:disappeared".format(ex.pid))


def main(args):
    """ Poll system for bad processes
    """
    logger = logging.getLogger(__name__)
    CONFIG['POLL'] = args.poll
    CONFIG['VERBOSE'] = args.verbose
    CONFIG['QUIET'] = args.quiet
    CONFIG['TEST_MODE'] = args.test
    CONFIG['CPU_THRESHOLD'] = args.cpu_threshold
    CONFIG['CPUTIME_THRESHOLD'] = args.cputime_threshold
    CONFIG['LOAD_THRESHOLD'] = args.load_threshold
    CONFIG['TIME_SCALE'] = args.time_scale
    CONFIG['DAEMON'] = args.daemon
    user = args.user

    LOGGER.debug("Active configuration:")
    for cfg_key, cfg_value in CONFIG.iteritems():
        LOGGER.debug("{0}: {1}".format(cfg_key, cfg_value))

    while(True):
        load = os.getloadavg()
        load = sum(load) / len(load)
        if load < CONFIG['LOAD_THRESHOLD']:
            time.sleep(CONFIG['POLL'])
            continue

        for bad in filter_processes(CONFIG['CPU_THRESHOLD'],
                                    time_scale_convert(
                                        CONFIG['CPUTIME_THRESHOLD']),
                                    user=user):
            try:
                nice = convert_nice(bad,
                    model='kernel',
                    time_scale=CONFIG['TIME_SCALE'])

                if not nice:
                    nice = convert_nice(bad,
                        model='relative',
                        time_scale=time_scale_convert(CONFIG['TIME_SCALE']))

                if nice != 0:
                    renice(bad, nice)

            except psutil.NoSuchProcess:
                continue
            
        time.sleep(CONFIG['POLL'])


if __name__ == "__main__":

    PARSER = argparse.ArgumentParser()
    PARSER.add_argument('--daemon',
        '-d',
        action='store_true',
        help="Fork into background")

    PARSER.add_argument('--logfile',
        '-L',
        action='store',
        default="",
        type=str,
        help="Log output to filename")

    PARSER.add_argument('--user',
        '-u',
        default="",
        type=str,
        help='Limit to specific user')    

    PARSER.add_argument('--cpu-threshold',
        '-c',
        default=CONFIG['CPU_THRESHOLD'],
        type=float,
        help='Trigger after n%%')

    PARSER.add_argument('--cputime-threshold',
        '-t',
        default=CONFIG['CPUTIME_THRESHOLD'],
        type=str,
        help='Trigger after {n}{smdwMy} Ex: 1d == 1 day')

    PARSER.add_argument('--load-threshold',
        '-l',
        default=CONFIG['LOAD_THRESHOLD'],
        type=float,
        help='Trigger after n load average')

    PARSER.add_argument('--time-scale',
        '-s',
        default=CONFIG['TIME_SCALE'],
        type=str,
        help="Time scale for nice value.\nFormat: {n}{smdwMy}\nEx: 1d == 1 day"
        )  
    
    PARSER.add_argument('--poll',
        '-p',
        default=CONFIG['POLL'],
        type=float,
        help='Wait n seconds between polling processes')

    PARSER.add_argument('--test',
        '-T',
        action='store_true',
        default=False,
        help='Do not modify processes; report only.')

    PARSER.add_argument('--verbose',
        '-v',
        action='store_true',
        default=False,
        help='Verbose output')

    PARSER.add_argument('--quiet',
        '-q',
        action='store_true',
        default=False,
        help='Suppress output')
    
    ARGUMENTS = PARSER.parse_args()

    FORMAT = "%(levelname)s:%(asctime)s:%(funcName)s:%(message)s"
    if ARGUMENTS.logfile:
        logging.basicConfig(filename=os.path.abspath(ARGUMENTS.logfile),
            format=FORMAT)
    else:
        logging.basicConfig(format=FORMAT) 

    logging.basicConfig(level=logging.INFO)
    LOGGER = logging.getLogger(__name__)
    LOGGER.setLevel(logging.INFO)

     
    if ARGUMENTS.verbose:
        LOGGER.setLevel(logging.DEBUG)

    if ARGUMENTS.test:
        LOGGER.debug('Test mode (processes will not be modified)')
    
    if ARGUMENTS.daemon:
        LOGGER.debug('Daemon mode')
        with daemon.DaemonContext():
            main(ARGUMENTS)
    else:
        LOGGER.debug('Foreground mode')
        main(ARGUMENTS)

