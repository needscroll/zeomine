import json
import hashlib
import random
import requests
import time
from selenium import webdriver
from bs4 import BeautifulSoup

## Step Crawler
#
class StepCrawler():
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

  ## Step Settings
  #
  # These take the form of a URL + action set
  settings['steps'] = []
  settings['url_variants'] = {}
  settings['action_variants'] = {}

  ## Behavior settings
  settings['crawler'] = {}
  settings['crawler']['selenium_browser'] = 'Firefox'
  settings['crawler']['selenium_browser_path'] = False

  # Extra plugins for acting when the Selenium Browser is open
  selenium_plugins = {}
  
  # Add the plugin names here. They must also be added/set up in Zeomine, as we will get the plugins there
  settings['selenium_plugins'] = []

  # Local data dict
  data = {}
  data['step_sets'] = []
  # DB cache - mainly meant to cache domain/URL IDs so we don't have to do select statements
  data['cache'] = {}
  data['cache']['domains'] = {}
  data['cache']['step_sets'] = {}
  data['cache']['steps'] = {}
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

  ###########
  # URL Functions

  # Get the database id for a domain. Try the cache first, then select, and finally create.
  def get_domain_id(self, string, recursed = False):
    if string in self.data['cache']['domains']:
      return self.data['cache']['domains'][string]
    else:
      d = self.z_obj.fetchone('select rowid from domains where domain=?', (string,))
      if d:
        return d[0]
      else:
        self.z_obj.ex('insert into domains values (?,NULL,NULL)',(string, ))
        if self.z_obj.cursor.lastrowid:
          return self.z_obj.cursor.lastrowid
        elif not recursed:
          return self.get_domain_id(string, True)
        else:
          return None

  # Get the database id for a url. Try the cache first, then select, and finally create.
  def get_url_id(self, string, recursed = False):
    if string in self.data['cache']['urls']:
      return self.data['cache']['urls'][string]
    else:
      d = self.z_obj.fetchone('select rowid from urls where url=?', (string,))
      if d:
        return d[0]
      else:
        # We don't he the URL info. In this crawler, we may not have the domain either, so grab it now
        dom = self.extract_domain(string)
        domain_id = False
        if dom:
          domain_id = self.get_domain_id(dom)
        if domain_id:
          # Now, insert our data
          self.z_obj.ex('insert into urls values (?,?)',(string, domain_id,))
          if self.z_obj.cursor.lastrowid:
            return self.z_obj.cursor.lastrowid
          elif not recursed:
            return self.get_url_id(string, True)
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

  ###########
  # Step data Functions

  # Get the database id for an element, searching by hash. If the hash isn't found, add to DB
  def get_step_set_id(self, hsh):
    d = self.z_obj.fetchone('select rowid from step_crawler_step_sets where hash=? and zeomine_instance=?', (hsh,self.z_obj.run_id))
    if d:
      return d[0]
    else:
      self.z_obj.excom('insert into step_crawler_step_sets values (?,?)',(self.z_obj.run_id,hsh,))
      self.data['cache'][hsh] = self.z_obj.cursor.lastrowid
      return self.z_obj.cursor.lastrowid

  # Get the database id for an element, searching by hash. If the hash isn't found, add to DB
  def get_step_id(self, hsh, stepsetid):
    d = self.z_obj.fetchone('select rowid from step_crawler_steps where hash=? and step_set=? and zeomine_instance=?', (hsh,stepsetid,self.z_obj.run_id))
    if d:
      return d[0]
    else:
      self.z_obj.excom('insert into step_crawler_steps values (?,?)',(self.z_obj.run_id,hsh,))
      self.data['cache'][hsh] = self.z_obj.cursor.lastrowid
      return self.z_obj.cursor.lastrowid

  ###########
  # Generate the step sets

  # Validates steps by checking that referenced data is present
  # The crawler may still generate errors from bad data
  def validate_step(self, step):
    # Check the URL
    if step['url']['type'] == 'variable' and step['url']['value'] not in self.settings['url_variants']:
      return False
    # Check the actions
    if step['actions']['type'] == 'variable' and step['actions']['value'] not in self.settings['action_variants']:
      return False
    return True

  def generate_variable_set(self, step):
    url_list = []
    actions_list = []
    # Url first
    if step['url']['type'] == 'constant':
      url_list = [step['url']['value']]
    elif step['url']['type'] == 'variable':
      v_set = step['url']['value']
      for url in self.settings['url_variants'][v_set]:
        url_list.append(url)
    # Now actions
    if step['actions']['type'] == 'constant':
      actions_list = [step['actions']['value']]
    elif step['actions']['type'] == 'variable':
      a_set = step['actions']['value']
      for actions in self.settings['action_variants'][a_set]:
        actions_list.append(self.settings['action_variants'][a_set][actions])
    # Put them together
    return_list = []
    for url in url_list:
      for actions in actions_list:
        return_list.append({'url': url, 'actions': actions})
    return return_list

  # TODO: Add recording of all steps/variants
  def generate_steps(self):
    step_sets = []
    for step in self.settings['steps']:
      if self.validate_step(step):
        # Take the existing list of step sets, and attach variants by creating new steps
        add_set = self.generate_variable_set(step)
        new_sets = []
        for aset in add_set:
          if step_sets:
            for step_set in step_sets:
              new_sets.append(step_set + [aset])
          else:
            new_sets.append([aset])
        step_sets = new_sets
    # Write step sets to database
    for step_set in step_sets:
      h = hashlib.sha256(str(step_set).encode()).hexdigest()
      self.z_obj.ex('INSERT INTO step_crawler_step_sets VALUES(?,?)',(self.z_obj.run_id, h))
      stepsetid = self.z_obj.cursor.lastrowid
      for step in step_set:
        data = (self.z_obj.run_id, )
        data += (stepsetid,)
        h = hashlib.sha256(str(step).encode()).hexdigest()
        data += (h,)
        data += (self.get_url_id(step['url']),)
        data += (str(step['actions']),)
        self.z_obj.ex('INSERT INTO step_crawler_steps VALUES(?,?,?,?,?)',data)
      self.z_obj.com()
        
    return step_sets

  ###########
  # Broswer actions to execute

  def action_record(self, item):
    if item == 'current_url':
      return self.browser.current_url
    elif item == 'cookies':
      return self.browser.get_cookies()

  def action_click(self,selector):
    try:
      self.browser.find_element_by_css_selector(selector).click()
      return 'done'
    except:
      return 'fail'

  def action_screencap(self):
    path = self.z_obj.settings['user_data']['base'] + self.z_obj.settings['user_data']['data']
    self.browser.save_screenshot(path + 'screenshot_' + str(time.time()) + '.png')
    return path

  def action_delete_cookies(self):
    self.browser.delete_all_cookies()
    return 'done'

  ###########
  # Execute the step sets

  def execute_action(self, action, index):
    # Get the verb
    verb = False
    noun = False
    if isinstance(action, str):
      verb = action
    elif isinstance(action, dict):
      # This is expected to be {verb: noun} format
      i = list(action.items())[0]
      verb = i[0]
      noun = i[1]
    # Check whether we have a noun, to load the approiate switch statement
    if noun:
      if verb == 'record':
        return self.action_record(noun)
      elif verb == 'click':
        return self.action_click(noun)
    else:
      if verb == 'screencap':
        return self.action_screencap()
      elif verb == 'delete_cookies':
        return self.action_delete_cookies()


  # Get data with Selenium module
  def walk_steps(self, step_set):
    h = hashlib.sha256(str(step_set).encode()).hexdigest()
    stepsetid = self.get_step_set_id(h)
    for step in step_set:
      h = hashlib.sha256(str(step).encode()).hexdigest()
      stepid = self.get_step_id(h, stepsetid)
      # Check if we are already at the listed URL. If not, go there
      if self.browser.current_url != step['url']:
        self.browser.get(step['url'])
      # Loop through the action set and do one at a time, entering data as we go
      for action in step['actions']:
        index = int(step['actions'].index(action))
        data = str(self.execute_action(action, index))
        act = (self.z_obj.run_id, )
        act += (stepid, )
        act += (index, )
        act += (str(action), )
        act += (data, )
        self.z_obj.ex('INSERT INTO step_crawler_data VALUES (?,?,?,?,?)', act)
      # Commit the data at the end of each step
      self.z_obj.com()

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
            elif section in self.settings:
              self.settings[section][subsection] = {}
              self.settings[section][subsection] = conf[section][subsection]
        # If not a dict, assume the section is a single property to set.
        else:
          if section in self.settings:
            self.settings[section] = conf[section]
    self.z_obj.pprint('Successfully loaded StepCrawler.', 2, 2)

  def initiate(self):
    self.z_obj.excom('CREATE TABLE IF NOT EXISTS step_crawler_step_sets (zeomine_instance text, hash text)')
    self.z_obj.excom('CREATE TABLE IF NOT EXISTS step_crawler_steps (zeomine_instance text, step_set int, hash text, url int, actions text)')
    self.z_obj.excom('CREATE TABLE IF NOT EXISTS step_crawler_data (zeomine_instance text, step int, action_index int, action text, data text)')
    self.data['step_sets'] = self.generate_steps()

  def crawl(self):
    for step_set in self.data['step_sets']:
      # We create a new browser for each step set
      path = self.settings['crawler']['selenium_browser_path']
      if path:
        brow = getattr(webdriver, self.settings['crawler']['selenium_browser'])(path)
        self.browser = brow
      else:
        brow = getattr(webdriver, self.settings['crawler']['selenium_browser'])()
        self.browser = brow
      # Walk through the steps:
      self.walk_steps(step_set)
      # We are done. Close the browser
      self.browser.quit()

  ## Shut down
  def shutdown(self):
    pass
