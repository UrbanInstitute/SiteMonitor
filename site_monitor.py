import requests
import datetime
import warnings
import time
from numpy import std, mean, random, NaN
from collections import defaultdict

class SiteMonitor():
    def __init__(self, categories=None, burn_in=100, choke_point=2, slow_down_thresh=20, speed_up_thresh=20, rand=None, start_delay=0, delays=None, handle_timer=True, rolling_mean_length=25):
        self.default = 'main' #a name used internally when only a single category is used, specified by the default, categories=None

        #turn the categories arg into a dict of lists
        if categories is None:
            self.responses = {self.default:[]}
        elif isinstance(categories, str):
            self.responses = {categories:[]}
        elif isinstance(categories, list):
            self.responses = {k:[] for k in categories}
        elif isinstance(categories, dict):
            assert(all([isinstance(v, list) for v in categories.values()])), 'If a dict is supplied to SiteMonitor, its values must all be lists.'
            if any([len(v) != 0 for v in categories.values()]):
                warnings.warn('The categories supplied to SiteMonitor contain values.  This may influence the results.')
            self.responses = categories
        else:
            raise InvalidCategory('Category must be None, a string, list or dict.')

        self.delay_tracker = defaultdict(lambda: 0)

        self.delays = {'burnin':10, 'min':0, 'max':30, 'interval':5, 'current':None}
        if delays is not None:
            assert(isinstance(delays, dict)), 'Delays argument must be None or a dict.'
            self.delays.update({k:v for k,v in delays.items() if k in self.delays.keys()})

        self.baseline_avg = {k:None for k in self.responses.keys()}
        self.baseline_std = {k:None for k in self.responses.keys()}
        self.baseline_max = {k:None for k in self.responses.keys()}
        self.rolling_mean = {k:[] for k in self.responses.keys()}
        self.burn_in = burn_in          #the number of responses recorded in a given category before comparison begins
        self.choke_point = choke_point  #the point, measured in std, above which a violation is counted
        self.slow_down_thresh = slow_down_thresh    #number of violations before a slowdown is triggered
        self.speed_up_thresh = speed_up_thresh      #number of safe rounds before a speed up is triggered
        self.num_violations = 0         #tracks the number of violations before a slowdown
        self.num_successes = 0          #tracks the number of successes before a speedup
        self.rand = rand                #None for no randomness in delay, otherwise a value in seconds
        self.start_delay = min(max(start_delay, self.delays['min']), self.delays['max'])  #the delay to default to after burn in is over
        self.burnin_over = {c:False for c in self.responses.keys()}
        self.handle_timer = handle_timer
        self.rolling_mean_length = rolling_mean_length

    def track_request(self, response, category=None):
        #turn the response arg into a float of seconds
        if isinstance(response, requests.models.Response):
            elapsed = response.elapsed.total_seconds()
        elif isinstance(response, datetime.timedelta):
            elapsed = response.total_seconds()
        elif isinstance(response, float) or isinstance(response, int):
            elapsed = response

        if category is None:
            category = self.default
        if category not in self.responses.keys():
            exception_str = '{} is not a valid category for this SiteMonitor instance.'
            raise InvalidCategory(exception_str)

        if len(self.responses[category]) < self.burn_in:
            delay = self._burnin_process(category, elapsed)
        elif len(self.responses[category]) == self.burn_in and self.burnin_over[category] is False:
            delay = self._end_burnin(category, elapsed)
        elif len(self.responses[category]) >= self.burn_in:
            delay = self._monitoring_process(category, elapsed)

        self.delay_tracker[delay] += 1
        if self.rand:
            delay = random.uniform(max(delay-self.rand, 0), delay+self.rand)

        if self.handle_timer:
            time.sleep(delay)
        else:
            return delay

    def _burnin_process(self, category, elapsed):
        #processes a response time when still in the burnin period (num of requests < burnin)
        self.responses[category].append(elapsed)

        return self.delays['burnin']

    def _end_burnin(self, category, elapsed):
        #calculates the baseline values when the burnin quantity of requests is reached for a
        #category, then runs the monitoring process.
        m = mean(self.responses[category])
        s = std( self.responses[category])

        self.baseline_avg[category] = m
        self.baseline_std[category] = s
        self.baseline_max[category] = m + self.choke_point*s
        self.delays['current'] = self.start_delay
        self.burnin_over[category] = True
        return self._monitoring_process(category, elapsed)

    def _monitoring_process(self, category, elapsed):
        #processes a response when out of the burnin period (num of requests >= burnin)
        self.responses[category].append(elapsed)
        rm = mean(self.responses[category][-self.rolling_mean_length:])
        self.rolling_mean[category].append(rm)

        if rm > self.baseline_max[category]:
            self.num_violations += 1
            if self.num_violations >= self.slow_down_thresh:
                #add to the delay
                self.delays['current'] += self.delays['interval']
                if self.delays['current'] > self.delays['max']:
                    self._halt_event(category)
                self.num_violations = 0
                self.num_successes = 0

        elif self.delays['current'] > self.delays['min']:
            self.num_successes += 1
            if self.num_successes >= self.speed_up_thresh:
                #reduce the delay
                self.delays['current'] -= self.delays['interval']
                self.delays['current'] = max(self.delays['current'], self.delays['min'])
                self.num_successes = 0
                self.num_violations = 0

        return self.delays['current']

    def _halt_event(self, category):
        # exception_str = 'Target site still slowed below baseline despite maximum delay reached. At {} for search category "{}"'.format(datetime.datetime.now(), category)
        # raise SiteMonitorHalt(exception_str)
        self.delays['current'] = self.delays['max']

    def report(self, action='save', path=None):
        import matplotlib.pyplot as plt
        from matplotlib.ticker import FormatStrFormatter

        lines = ['r-', 'b-', 'c-', 'g']*3
        fig = plt.figure(figsize=(12, 6))
        subs = []
        for i, cat in enumerate(self.responses.keys()):
            ax = fig.add_subplot(len(self.responses),1,i+1)
            y = range(len(self.responses[cat]))
            if len(self.responses[cat]) < self.burn_in:
                ax.plot(y, self.responses[cat], 'k.', markersize=.6, linewidth=.7)
            else:
                ax.plot(y, self.responses[cat], 'k.', y, [NaN]*self.burn_in+self.rolling_mean[cat], lines[i], markersize=.6, linewidth=.7)
            ax.yaxis.set_major_formatter(FormatStrFormatter('%.1f'))
            ax.set_ylabel(cat)
            subs.append(ax)

        max_right_x = max([lim.get_xlim()[1] for lim in subs])
        for ax in subs:
            ax.set_xlim(0, max_right_x)
            ax.axvline(x=self.burn_in, linestyle='dashed', label='burn-in', linewidth=.5, color='k')
            label = ax.get_ylabel()
            if self.baseline_max[label] is not None:
                #ymax = max(self.baseline_max[label]*1.2, ax.get_ylim()[1])
                ymax = self.baseline_max[label]*2
                ymin = min(self.responses[label])*.8
                #ax.set_ylim(ax.get_ylim()[0], ymax)
                ax.set_ylim(ymin, ymax)
                ax.axhline(y=self.baseline_max[label], linestyle='dashed', linewidth=.5, color='r')

        #if there is more than one subplot, remove the x labels from all that aren't on the bottom
        if len(subs) > 1:
            for ax in subs[:-1]:
                ax.set_xticklabels([])

        #text over the top plot for the burn in line
        subs[0].text(self.burn_in, subs[0].get_ylim()[1]*1.05, 'burn-in', horizontalalignment='center', style='italic')

        #an x label for the last plot
        subs[-1].set_xlabel('Number of Responses')

        if action == 'display':
            plt.show()
        elif action == 'save':
            import os
            if path is None:
                path = os.path.dirname(os.path.realpath(__file__))
            else:
                fig.savefig(os.path.join(path, 'search_report.png'))
                plt.close('all')

class InvalidCategory(Exception):
    pass

class SiteMonitorHalt(Exception):
    pass
