import json
import random
import requests
import time
from selenium import webdriver
from bs4 import BeautifulSoup
from selenium.webdriver.firefox.options import Options
import selenium.webdriver.chrome.service as service

## Core Crawler
#
class CoreCrawler():
  ##############################################################################
  # Plugin Settings
  ##############################################################################
  
  # Define the parent ZSM object so we can call its functions and access its 
  # data. Set this in load_config
  z_obj = None

  # Browser object (for Selenium)
  browser = None

  # Settings dict
  settings = {}

  ## General Settings
  settings['domain'] = 'example.com'
  settings['https'] = False # True: https://, false: http://
  settings['internal_exts'] = ['htm', 'html', 'asp', 'aspx', 'php']
  # Max number of errors to permit before turning on "debug mode" to force the crawler to stop.
  settings['error_max'] = 10
  settings['load_uncrawled'] = False # Load uncrawled URLs
  settings['save_uncrawled'] = False # Save uncrawled URLs

  ## Behavior settings
  # Crawl delay and path whitelist/blacklist. May be modified by a site's robots.txt
  settings['crawler'] = {}
  settings['crawler']['robots_txt'] = True # Look at robots.txt first
  settings['crawler']['req_delay'] = {}
  settings['crawler']['req_delay']['method'] = 'static' # Delay calculation method. See self.calculate_delay
  settings['crawler']['req_delay']['time'] = 0 # Delay calculation method. See self.calculate_delay
  # 'selenium' or 'requests'
  settings['crawler']['req_method'] = 'requests'
  # Add failed URLs back into the queue. Will not retry immediately, but will
  # instead append URLs to the end of the queue.
  settings['crawler']['retry_on_error'] = True
  # Time until browser times out
  # TODO add to requests engine
  settings['crawler']['timeout'] = 30
  # Skip previously crawled items
  settings['crawler']['skip_crawled'] = False
  #Selenium browser + location of driver/browser binaries
  settings['crawler']['selenium_browser'] = 'Firefox'
  settings['crawler']['selenium_driver_path'] = False
  settings['crawler']['selenium_browser_path'] = False
  ## In development - modifies certain Firefox behaviors
  settings['crawler']['browser_settings'] = {}
  settings['crawler']['browser_settings']['headless'] = True
  settings['crawler']['browser_settings']['disable_javascript'] = False

  # Subdomain settings
  settings['subdomains'] = {}
  settings['subdomains']['allow'] = False
  settings['subdomains']['whitelist'] = []
  settings['subdomains']['blacklist'] = []
  
  ## Link settings
  settings['links'] = {}
  # Selectors for extracting links. Dict with selector as key, list of allowed data properties as value
  settings['links']['selectors'] = {'a': ['href']}
  # Crawl randomly. True: Go through links randomly, False: go through a list (permits prioritization)
  settings['links']['random'] = False
  # Do not read links below a certain depth.
  settings['links']['max_depth'] = False
  # Exclude URLs with any of the following substrings
  settings['links']['exclude_str'] = []
  # Require URLs with any of the following substrings
  settings['links']['require_str'] = []
  # Exclude internal, external, or file type links. Enter as strings in a list
  settings['links']['exclude_type'] = []
  # Max number of links to crawl, before going on to the next step. 0 for no limit
  settings['links']['max_links'] = {'internal': 0, 'external': 0, 'file': 0, 'total': 0}
  # Max time to give to a given link set, before going on to the next step. 0 for no limit
  settings['links']['max_time'] = {'internal': 0, 'external': 0, 'file': 0, 'total': 0}
  # Add a set of links to start
  settings['links']['initial_urls'] = {'internal': [], 'external': [], 'file': []}

  # Extra plugins for acting when the Selenium Browser is open
  selenium_plugins = {}

  # Extra plugins for acting when deermining whether a URL is crawled
  check_crawled_plugins = {}
  
  # Add the Selenium post-GET plugin names here. They must also be added/set up in Zeomine, as we will get the plugins there
  settings['selenium_plugins'] = []
  
  # Add the "Check Crawled" plugin names here. They must also be added/set up in Zeomine, as we will get the plugins there
  settings['check_crawled_plugins'] = []

  # Local data dict
  data = {}
  data['active_domain'] = ''
  data['error_count'] = 0

  data['urls_to_crawl'] = {'internal': [], 'external': [], 'file': []}
  data['crawled_urls'] = {'internal': [], 'external': [], 'file': []}
  data['url_counts'] = {'internal': 0, 'external': 0, 'file': 0, 'total': 0}
  # DB cache - mainly meant to cache domain/URL IDs so we don't have to do select statements
  data['cache'] = {}
  data['cache']['domains'] = {}
  data['cache']['domain_info'] = {}
  data['cache']['urls'] = {}

  ##############################################################################
  # Helper Functions
  ##############################################################################

  ###########
  # Common data functions

  # Check against whitelist: item contains a matching substring
  def in_whitelist(self, item, whitelist):
    if not whitelist:
      return True
    else:
      for substr in whitelist:
        if substr in item:
          return True
      return False

  # Check against blacklist: item does not contain a matching substring
  def in_blacklist(self, item, blacklist):
    if not blacklist:
      return False
    else:
      for substr in blacklist:
        if substr in item:
          return True
      return False

  def calculate_delay(self, method, t = 0):
    if method == 'static':
      return t
    else:
      return 0

  ###########
  # Domain/URL Functions

  # Get the database id for a domain. Try the cache first, then select, and finally create.
  def get_domain_id(self, string, https = None, recursed = False):
    if string in self.data['cache']['domains']:
      return self.data['cache']['domains'][string]
    else:
      d = self.z_obj.fetchone('select rowid from domains where domain=?', (string,))
      if d:
        return d[0]
      else:
        h = self.settings['https'] if not https else https
        self.z_obj.ex('insert into domains values (?,?,NULL)',(string, h,))
        if self.z_obj.cursor.lastrowid:
          return self.z_obj.cursor.lastrowid
        elif not recursed:
          return self.get_domain_id(string, https, True)
        else:
          return None

  # Get the domain info from an id. Check the cache first. 
  # Assumes domain info was created from get_domain_id already.
  def get_domain_info(self, domain_id):
    if domain_id in self.data['cache']['domain_info']:
      return self.data['cache']['domain_info'][domain_id]
    else:
      d = self.z_obj.fetchone('select * from domains where rowid=?', (domain_id,))
      if d:
        self.data['cache']['domain_info'][domain_id] = d
        return d
      else:
        return None

  # Get the database id for a url. Try the cache first, then select, and finally create.
  def get_url_id(self, string, domain_id, recursed = False):
    if string in self.data['cache']['urls']:
      return self.data['cache']['urls'][string]
    else:
      d = self.z_obj.fetchone('select rowid from urls where url=?', (string,))
      if d:
        return d[0]
      else:
        self.z_obj.ex('insert into urls values (?,?)',(string, domain_id,))
        if self.z_obj.cursor.lastrowid:
          return self.z_obj.cursor.lastrowid
        elif not recursed:
          return self.get_url_id(string, domain_id, True)
        else:
          return None

  # Extract domain from url
  def extract_domain(self, url):
    if url and 'http' in url:
      url_parts = url.split('/')
      if len(url_parts) >= 3:
        return url_parts[2]
      else:
        return None
    else:
      return None

  # Determine URL type
  def get_url_type(self, url):
    # Relative URLs are definitely not external
    if 'http' not in url:
      # Assumption: paths without a filename-y extension are in fact web pages.
      # The one clear exception would be API and other endpoints that 
      # would only be revealed in headers. TODO: in the crawl step, check for this case and update accordingly
      url_parts = url.split('/')
      last_part = url_parts[-1]
      if '.' not in last_part:
        return 'internal'
      else:
        ret = 'file'
        for ext in self.settings['internal_exts']:
          ext = '.'.join(['',ext])
          if url.endswith(ext):
            ret = 'internal'
        return ret
    # Next, check the domain. TODO add subdomain handling
    else:
      url_parts = url.split('/')
      domain = self.extract_domain(url)
      if domain and domain == self.data['active_domain']:
        if len(url_parts) == 3:
          # We have the domain root
          return 'internal'
        else:
          new_url = '/'.join(url_parts[3:])
          return self.get_url_type(new_url)
      elif self.settings['subdomains']['allow']:
        if self.in_whitelist(domain, self.settings['subdomains']['whitelist']) \
        and self.in_whitelist(domain, [self.settings['domain']]) \
        and not self.in_blacklist(domain, self.settings['subdomains']['blacklist']):
          # Get the domain info, then set subdomain if needed
          i = self.get_domain_id(domain)
          d = self.get_domain_info(i)
          did = self.get_domain_id(self.settings['domain'])
          if d[2] != did:
            self.z_obj.ex('UPDATE domains SET subdomain_of=? WHERE rowid=?', (did, i))
            l = list(self.data['cache']['domain_info'][i])
            l[2] = did
            self.data['cache']['domain_info'][i] = tuple(l)
          return 'internal'
        else:
          return 'external'
      else:
        return 'external'

  # Is the URL excluded from being added?
  def is_excluded(self, url):
    for substr in self.settings['links']['exclude_str']:
      if substr in url:
        return True
    return False
  
  # Does the URL have a required string?
  def is_required(self, url):
    if self.settings['links']['require_str']:
      for substr in self.settings['links']['require_str']:
        if substr in url:
          return True
      return False
    else:
      return True

  ###########
  # Crawl/Add Logic

  # Get a URL's data, and add it to the list
  def crawl_url(self, url, url_type, domain_id):
    if self.settings['crawler']['req_method'] == 'requests':
      self.requests_get_data(url, url_type, domain_id)
    if self.settings['crawler']['req_method'] == 'selenium':
      self.selenium_get_data(url, url_type, domain_id)

  # Get data with Selenium module
  def selenium_get_data(self, url, url_type, domain_id):
    insert_data = ()
    u = url['url']
    uid = self.get_url_id(url['url'], domain_id)
    # Make a GET request and record data
    s = time.time()
    self.browser.get(u)
    e = time.time()
    # Reset the screen each time
    self.browser.set_window_size(1280,960)
    # Record Data
    req_text = self.browser.find_element_by_tag_name("html").get_attribute('innerHTML')
    insert_data = insert_data + (self.z_obj.run_id,)
    insert_data = insert_data + (uid,)
    insert_data = insert_data + (url_type,)
    insert_data = insert_data + (url['depth'],)
    insert_data = insert_data + (None,)
    insert_data = insert_data + (round((e - s), 4),)
    self.z_obj.ex('insert into crawler_basic_data values (?,?,?,?,?,?)', insert_data)
    cbi = self.z_obj.cursor.lastrowid
    self.z_obj.ex('insert into crawler_req_text values (?,?,?)', (self.z_obj.run_id, cbi, req_text))
    if req_text and url_type == 'internal':
      self.get_links(url, req_text, domain_id)
    for plugin in self.selenium_plugins:
      if callable(getattr(self.selenium_plugins[plugin], 'core_crawler_selenium', False)):
        self.selenium_plugins[plugin].core_crawler_selenium(u, uid)

  # Get data with Requests module
  def requests_get_data(self, url, url_type, domain_id):
    insert_data = ()
    head = {'User-Agent': self.z_obj.settings['user_agent']}
    s = time.time()
    req = requests.get(url['url'], headers=head)
    e = time.time()
    insert_data = insert_data + (self.z_obj.run_id,)
    insert_data = insert_data + (self.get_url_id(url['url'], domain_id),)
    insert_data = insert_data + (url_type,)
    insert_data = insert_data + (url['depth'],)
    insert_data = insert_data + (req.status_code,)
    insert_data = insert_data + (round((e - s), 4),)
    self.z_obj.ex('insert into crawler_basic_data values (?,?,?,?,?,?)', insert_data)
    cbi = self.z_obj.cursor.lastrowid
    self.z_obj.ex('insert into crawler_req_text values (?,?,?)', (self.z_obj.run_id, cbi, req.text))
    self.z_obj.ex('insert into crawler_req_headers values (?,?,?)', (self.z_obj.run_id, cbi, json.dumps(dict(req.headers))))
    if req.status_code == 200 and url_type == 'internal':
      self.get_links(url, req.text, domain_id)

  # Adds links to the crawl list, returns the outbound link count, and builds the inbound link count
  def get_links(self, url, url_text, domain_id):
    parse = BeautifulSoup(url_text, 'html.parser')
    link_set = []
    for selector in self.settings['links']['selectors']:
      for item in parse.find_all(selector):
        for prop in self.settings['links']['selectors'][selector]:
          u = item.get(prop)
          # Get the full URL and its domain info
          if u and not self.is_excluded(u) and self.is_required(u):
            dom = self.extract_domain(u)
            di = 0
            add = {}
            if dom:
              di = self.get_domain_id(dom)
              d_info = self.get_domain_info(di)
              add = {'url': u, 'depth': url['depth'] + 1}
            else:
              di = domain_id
              d_info = self.get_domain_info(di)
              pre = 'https://' if d_info[1] else 'http://'
              add_url = ''.join([pre, d_info[0], u])
              add = {'url': add_url, 'depth': url['depth'] + 1}
            if add and di:
              typ = self.get_url_type(add['url'])
              # Create a link
              fro = self.get_url_id(url['url'], domain_id)
              to = self.get_url_id(add['url'], di)
              link_set.append((self.z_obj.run_id, fro, to))
              ## Add to crawl list
              # If 'skip_crawled' is set, then we will search all instances, not just the current one.
              # TODO add plugin checks
              check1 = False
              if self.settings['crawler']['skip_crawled']:
                check1 = self.z_obj.fetchone('select * from crawler_basic_data where url=?', (to,))
              else:
                check1 = self.z_obj.fetchone('select * from crawler_basic_data where zeomine_instance=? and url=?', (self.z_obj.run_id, to))
              check2 = list(filter(lambda a: a['url'] == add['url'], self.data['urls_to_crawl'][typ]))
              if not check1 and not check2:
                self.z_obj.pprint(': '.join(["Adding", add['url']]), 2)
                self.data['urls_to_crawl'][typ].append(add)
    self.z_obj.exm('insert into links values (?,?,?)',link_set)
  
  # Removes previously crawled URLs
  # This is called just before crawling starts, and removes items which have already been crawled in another instance.
  def remove_crawled(self):
    for typ in sorted(self.data['urls_to_crawl'], reverse = True):
      for url in self.data['urls_to_crawl'][typ]:
        #If it isn't in the crawler data, it wasn't crawled. If it was, check the plugins.
        domain = self.extract_domain(url['url'])
        domain_id = self.get_domain_id(domain)
        url_id = self.get_url_id(url['url'], domain_id)
        crawlercheck = self.z_obj.fetchone('select * from crawler_basic_data where url=?', (url_id,))
        if crawlercheck:
          rem = True
          for plugin in self.selenium_plugins:
            if callable(getattr(self.check_crawled_plugins[plugin], 'check_crawled', False)):
              # True: URL already crawled and data recorded - remove
              # False: URL not crawled yet - do not remove
              if not self.check_crawled_plugins[plugin].check_crawled(url, url_id):
                rem = False
          if rem:
            self.z_obj.pprint('Removing ' + url['url'] + ' as it was already crawled', 2)
            self.data['urls_to_crawl'][typ].remove(url)
        else:
          pass
    
  
  ###########
  # Initiate/Restart Browser
  
  # Initiate a brower instance
  def initiate_browser(self):
    path = self.settings['crawler']['selenium_driver_path']
    if self.settings['crawler']['selenium_browser'] == 'Firefox':
      fp = webdriver.FirefoxProfile()
      if self.settings['crawler']['browser_settings']['disable_javascript']:
        fp.set_preference("javascript.enabled", 'false')
      #~ fp.set_preference('dom.ipc.plugins.enabled.libflashplayer.so', 'false')
      options = Options()
      if self.settings['crawler']['browser_settings']['headless']:
        options.set_headless(True)
      if path:
        brow = getattr(webdriver, self.settings['crawler']['selenium_browser'])(path, firefox_profile=fp, options=options)
        self.browser = brow
      else:
        brow = getattr(webdriver, self.settings['crawler']['selenium_browser'])(firefox_profile=fp, options=options)
        self.browser = brow
    elif self.settings['crawler']['selenium_browser'] == 'Chrome':
      serv = None
      if path:
        serv = service.Service(path)
      else:
        self.z_obj.pprint('Chrome requires a path to be set for Chromedriver', -1)
        exit()
      serv.start()
      if self.settings['crawler']['selenium_browser_path']:
        capabilities = {'chrome.binary': self.settings['crawler']['selenium_browser_path']}
        brow = webdriver.Remote(serv.service_url, capabilities)
        self.browser = brow
      else:
        brow = webdriver.Remote(serv.service_url, capabilities)
        self.browser = brow
    else:
      if path:
        brow = getattr(webdriver, self.settings['crawler']['selenium_browser'])(path)
        self.browser = brow
      else:
        brow = getattr(webdriver, self.settings['crawler']['selenium_browser'])()
        self.browser = brow
    self.browser.set_page_load_timeout(self.settings['crawler']['timeout'])
  
  def restart_browser(self):
    if self.settings['crawler']['req_method'] == 'selenium':
      try:
        self.browser.quit()
        self.initiate_browser()
      except:
        self.z_obj.pprint('Failed to restart browser', 0)

  ##############################################################################
  # Zeomine plugins
  ##############################################################################

  def load_config(self):
    # If we have settings, load them.
    if 'settings' in self.z_obj.conf['crawler']:
      conf = self.z_obj.conf['crawler']['settings']
      for section in conf:
        if isinstance(conf[section], dict):
          for subsection in conf[section]:
            if section in self.settings and subsection in self.settings[section]:
              self.settings[section][subsection] = conf[section][subsection]
        # If not a dict, assume the section is a single property to set.
        else:
          if section in self.settings:
            self.settings[section] = conf[section]
    if self.settings['selenium_plugins']:
      for plug in self.settings['selenium_plugins']:
        if plug in self.z_obj.plugins:
          self.selenium_plugins[plug] = self.z_obj.plugins[plug]
          self.selenium_plugins[plug].parent_obj = self
    if self.settings['check_crawled_plugins']:
      for plug in self.settings['check_crawled_plugins']:
        if plug in self.z_obj.plugins:
          self.check_crawled_plugins[plug] = self.z_obj.plugins[plug]
          self.check_crawled_plugins[plug].parent_obj = self
    
    # We need to set the active domain for certin items which need it in initiate()
    self.data['active_domain'] = self.settings['domain']
    
    # Add initial URLs
    for typ in self.settings['links']['initial_urls']:
      for u in self.settings['links']['initial_urls'][typ]:
        self.data['urls_to_crawl'][typ].append({'url': u, 'depth': 0})
    
    self.z_obj.pprint('Successfully loaded CoreCrawler.', 2, 2)

  def initiate(self):
    self.z_obj.excom('CREATE TABLE IF NOT EXISTS crawler_basic_data (zeomine_instance text, url int, type text, depth int, status text, load_time real)')
    self.z_obj.excom('CREATE TABLE IF NOT EXISTS crawler_req_text (zeomine_instance text, crawl_data int, response_text text)')
    self.z_obj.excom('CREATE TABLE IF NOT EXISTS crawler_req_headers (zeomine_instance text, crawl_data int, response_headers text)')
    self.z_obj.excom('CREATE TABLE IF NOT EXISTS links (zeomine_instance text, from_url int, to_url int)')
    if self.settings['crawler']['req_method'] == 'selenium':
      self.initiate_browser()
    

  def load_previous_state(self):
    if self.settings['load_uncrawled']:
      try:
        uncrawled = self.z_obj.fetchall('SELECT * from uncrawled_urls')
        for u in uncrawled:
          add = {'url': u[0],'depth': u[2]}
          self.data['urls_to_crawl'][u[1]].append(add)
        self.z_obj.excom('DELETE FROM uncrawled_urls')
        self.z_obj.excom('VACUUM')
      except:
        pass

  def crawl(self):
    # Check that the domain is in the DB. TODO: add subdomain support
    domain_id = self.get_domain_id(self.settings['domain'])
    self.data['active_domain'] = self.settings['domain']
    # Create the first URL if the internal url list is empty
    if not self.data['urls_to_crawl']['internal']:
      pre = 'https://' if self.settings['https'] else 'http://'
      first_url = ''.join([pre, self.settings['domain']])
      self.data['urls_to_crawl']['internal'].append({'url': first_url, 'depth': 0})
    # Clean up the list of previously crawled URLs, e.g. in the case of using URLListBuilder or after
    # a previous crawl that failed with an error.
    if self.settings['crawler']['skip_crawled']:
      self.remove_crawled()
    # Crawl through each type of url
    crawl_start_all = time.time()
    i = 0
    for typ in sorted(self.data['urls_to_crawl'], reverse = True):
      if typ not in self.settings['links']['exclude_type']:
        crawl_start = time.time()
        while self.data['urls_to_crawl'][typ] \
        and (self.data['url_counts'][typ] < self.settings['links']['max_links'][typ] or not self.settings['links']['max_links'][typ]) \
        and (self.data['url_counts']['total'] < self.settings['links']['max_links']['total'] or not self.settings['links']['max_links']['total']) \
        and (time.time() - crawl_start <= self.settings['links']['max_time'][typ] or not self.settings['links']['max_time'][typ]) \
        and (time.time() - crawl_start <= self.settings['links']['max_time']['total'] or not self.settings['links']['max_time']['total']):
          i += 1
          # Pick the url to crawl
          if self.settings['links']['random']:
            random.shuffle(self.data['urls_to_crawl'][typ])
          url = self.data['urls_to_crawl'][typ].pop(0)
          # Crawl the page
          self.z_obj.pprint(''.join(["Crawling #", str(i), ': ', url['url']]), 1)
          if self.z_obj.debug_mode:
            self.crawl_url(url, typ, domain_id)
          else:
            try:
              self.crawl_url(url, typ, domain_id)
              self.data['error_count'] = 0
            except:
              self.data['error_count'] += 1
              self.z_obj.pprint('Crawl Error ' + str(self.data['error_count']), 0)
              # Add the url back into the queue if we have that option set
              if self.settings['crawler']['retry_on_error']:
                self.data['urls_to_crawl'][typ].append(url)
              # Sometimes the issue is the browser failing. This will fix it.
              self.restart_browser()
              if self.data['error_count'] >= self.settings['error_max']:
                # We are probably going to crash. Save everything!
                self.shutdown()
                # Since shutdown() turns off the Selenium Browser, we need to turn it back on in this case:
                if self.settings['crawler']['req_method'] == 'selenium':
                  self.initiate_browser()
                # Turn on debug mode.
                # You are probably going to crash: usually you are here
                # because something went wrong and isn't self-correcting.
                self.z_obj.debug_mode = True
          self.data['url_counts'][typ] += 1
          self.data['url_counts']['total'] += 1
          # Write any uncommitted data
          self.z_obj.com()
          time.sleep(self.calculate_delay(self.settings['crawler']['req_delay']['method'], self.settings['crawler']['req_delay']['time']))

  ## Write the uncrawled URLs to fill for later parsing
  def shutdown(self):
    # We are done crawling at this point, so shut the browser down.
    if self.settings['crawler']['req_method'] == 'selenium':
      self.browser.quit()
    # Save uncrawled URLs if need be:
    if self.settings['save_uncrawled']:
      self.z_obj.excom('CREATE TABLE IF NOT EXISTS uncrawled_urls (url text, type text, depth int)')
      for typ in sorted(self.data['urls_to_crawl'], reverse = True):
        for url in self.data['urls_to_crawl'][typ]:
          self.z_obj.ex('INSERT INTO uncrawled_urls VALUES (?,?,?)',(url['url'], typ, url['depth']))
      self.z_obj.com()
