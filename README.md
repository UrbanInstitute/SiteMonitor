# SiteMonitor

Code by Jeff Levy (jlevy@urban.org), 2017

Code provided as-is, without warranty; free to use it for your projects but please understand the code before relying upon it.

*A generalized tool for use with scraping projects that monitors the response time of the website being scraped and adjusts the delay.*

SiteMonitor(categories=None, burn_in=100, choke_point=2, slow_down_thresh=20, speed_up_thresh=20, rand=None, start_delay=0, delays=None, handle_timer=True, rolling_mean_length=50)
  - **categories** (*None, str, list, dict*) Allows you to track the timing of different types of responses, e.g. if the progam makes a request to a landing page, followed by a request to search a database, it's reasonable to assume those have different response times by their nature.  Defaults to None for when there is only one category.
  - **burn_in** (*int*) The number of requests measured per category to establish a baseline response time.  Default 100.
  - **choke_point** (*int, float*) The number of standard deviations above the mean the rolling mean of the response time must surpass before it is considered a violation.  Default 2.
  - **slow_down_thresh** (*int*) The number of times the rolling mean of responses must come in above the choke_point before the a slow down is triggered.  Default 20.
  - **speed_up_thresh** (*int*) The number of times the rolling mean responses must come in below the choke_point before the a speed up is triggered.  Default 20.
  - **rand** (*None, int, float*) Randomness added to the delay.  Defaults to None; any other value will be the minimum and maximum bounds from the non-random value for the uniform distribution the actual delay is drawn from.  E.g. if SiteMonitor would return a 5 second delay, but rand=1, then it will return uniform(4, 6) instead.
  - **start_delay** (*int*) After the burn-in period finishes, this is the starting delay in seconds.  Defaults to 0.
  - **delays** (*dict*) Modifies the default values for the seconds delay during the burnin period ("burnin", default 10), the minimum allowable ("min", default 0), the maximum allowable ("max", default 30), and the interval speed up and slow down events change the current delay by ("interval", default 5).  None, one or all of the keys can be passed in the dict.
  - **handle_timer** (bool) Defaults to True, where the delay is processed by the SiteMonitor instance.  When False, the delay is only returned as a value by the track_request method.
  - **rolling_mean_length** (int) How far back in the history to look when calculating the current average response time.  Defaults to 50.
  
SiteMonitor.track_request(response, category=None)
  - **response** (*requests.Response, datetime.timedelta, int, float*) The object representing one search.  Can be a complete get or post request from the Requests module, a timedelta, or a float or int representing seconds elapsed.
  - **category** (*None, str*) The type of response; see the description of the same kwarg from the SiteMonitor initialization above.

SiteMonitor.report(action='save')
  - **action** (*str*) When set to *display*, it shows the graph.  When set to *save*, it writes it to disk.

Note that in order to import site_monitor, you will need to add the folder it is in to your Python path using, for example, *sys.path.append('c:\users\...\github\sitemonitor\)*
  
```python
from site_monitor import *
import requests
import time

sm = SiteMonitor()

for _ in range(101):
	response = requests.get('http://www.google.com')
	delay = sm.track_request(response)
	time.sleep(delay)

print(sm.baseline_avg) #the average response time of the first 100 searches
print(sm.baseline_std) #the standard deviation
print(sm.baseline_max) #the top cutoff: average + 2*std
print(sm.responses)    #the list of all response times
```

Or an example with multiple categories that calls the *report* method at the end:

```python
from numpy import random

sm = SiteMonitor(categories=['landing', 'search', 'query'], handle_timer=False)

for _ in range(50):
    delay = sm.track_request(random.uniform(.5, 5), 'landing')
    delay = sm.track_request(random.uniform(2, 5), 'query')
    delay = sm.track_request(random.uniform(1, 5), 'search')
   
for _ in range(100):
    delay = sm.track_request(random.uniform(.5, 5), 'landing')
    delay = sm.track_request(random.uniform(4, 6), 'query')
    delay = sm.track_request(random.uniform(1, 5), 'search')
	
for _ in range(400):
    delay = sm.track_request(random.uniform(6, 11), 'landing')
    delay = sm.track_request(random.uniform(.5, .9), 'query')
    delay = sm.track_request(random.uniform(1, 5), 'search')
	
	
sm.report('display')
```

Which displays:

![SiteMonitor report](https://user-images.githubusercontent.com/5167516/47364166-e9e24400-d6d8-11e8-8ee1-e5f65fec8bac.png)
