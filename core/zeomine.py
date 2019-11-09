import importlib
import json
import os
import sqlite3
import sys
import time
import uuid
import yaml
from collections import OrderedDict
from datetime import datetime
from os import mkdir

from core.utilities.zeomine_common import TimeoutException

# Zeomine Python class
class Zeomine():
  ##############################################################################
  # Settings, config, and data
  ##############################################################################

  # Debug mode: Use this to bypass certain try/accept blocks
  debug_mode = False

  # Settings dict and settings defaults
  settings = {}

  settings['description'] = 'Zeomine Web Crawler'
  # User agent to be used by crawler, plugins, etc.
  settings['user_agent'] = 'Zeomine Web Crawler 2.x'

  settings['verbosity'] = 0
  settings['log_verbosity'] = 0

  settings['user_data'] = {}
  settings['user_data']['base'] = 'user_data/'
  settings['user_data']['data'] = 'data/'
  settings['user_data']['config'] = 'configs/'
  settings['user_data']['log'] = 'logs/'
  settings['output_path'] = False
  settings['log_path'] = 'zeomine_default.log'

  # DB File path, relative to user data directory
  settings['db_path'] = 'zeomine_data.db'

  # Config dict
  conf = {}
  conf['crawler'] = {}
  conf['plugins'] = {}

  # Data dict
  data = {}
  data['alerts'] = []
  data['metadata'] = {}
  data['plugins'] = {}

  # Database
  db = None
  
  # Run ID: Get this when we start up the database
  run_id = 0

  # Crawler
  crawler = {}

  # Plugins
  plugins = {}

  ##############################################################################
  # Init and helper functions
  ##############################################################################
  
  # Init function
  def __init__(self, config_path, debug = False):
    self.settings['config_path'] = config_path
    self.debug_mode = debug

  # Internal print function that also handles logging and file output
  def pprint(self, text, verbosity_threshold = 1, log_verbosity_threshold = 1):
    s = str(text)
    if log_verbosity_threshold <= self.settings['log_verbosity']:
      with open(self.settings['user_data']['base'] + self.settings['user_data']['log'] + self.settings['log_path'], 'a') as f:
        f.write(s + '\n')
    else:
      pass
    if verbosity_threshold <= self.settings['verbosity']:
      if self.settings['output_path']:
        with open(self.settings['user_data']['base'] + self.settings['user_data']['log'] + self.settings['output_path'], 'a') as f:
          f.write(s + '\n')
      else:
        sys.stdout.write(s + '\n')
        sys.stdout.flush()
    else:
      pass

  # Generate startup metadata
  def generate_metadata(self):
    now = datetime.now()
    timestamp = time.mktime(now.timetuple())
    self.data['metadata']['uuid'] = str(uuid.uuid4())
    self.data['metadata']['time'] = int(timestamp)
    self.data['metadata']['time_format'] = now.strftime('%Y-%m-%d-%H:%M:%S.%f')

  # Load a config file
  def load_config_file(self,path):
    with open(path, 'r') as f:
      # Loop through everything in the config file, and set self.conf to file's configuration
      c = yaml.load(f)
      # Load settings
      sets = c['settings']
      for s in sets:
        self.settings[s] = sets[s]
      # Load configs
      config = c['conf']
      for item in config:
        # If we are looking at a plugin, loop through each plugin
        if item == 'plugins':
          for plug in config['plugins']:
            self.conf['plugins'][plug] = config['plugins'][plug]
        else:
          self.conf[item] = config[item]

  # Load the crawler or a plugin
  def load_components(self, typ, conf_base, component_bases):
    c = conf_base['class']
    m = importlib.import_module(component_bases[conf_base['type']] + '.' + conf_base['module'])
    comp = getattr(m,c)
    if typ == 'crawler':
      self.crawler = comp()
      self.crawler.z_obj = self
    elif typ == 'plugins':
      # Check to see if we already added this plugin
      chk = []
      for plu in self.plugins:
        chk.append(str(plu.__class__))
      if str(c) not in chk:
        # We can add this plugin. Also, set the z_obj
        self.plugins[c] = comp()
        self.plugins[c].z_obj = self

  ####################
  ## DB Commands

  # Fetch one item from a select statement
  def fetchone(self, command, data = False):
    if data:
      r = self.cursor.execute(command, data)
      ret = r.fetchone()
    else:
      r = self.cursor.execute(command)
      ret = r.fetchone()
    return ret

  # Fetch all items from a select statment
  def fetchall(self, command, data = False):
    if data:
      r = self.cursor.execute(command, data)
      ret = r.fetchall()
    else:
      r = self.cursor.execute(command)
      ret = r.fetchall()
    return ret

  # Execute a DB command
  def ex(self, command, data = False):
    if data:
      self.cursor.execute(command, data)
    else:
      self.cursor.execute(command)

  # Execute many DB commands
  def exm(self, command, data = False):
    if data:
      self.cursor.executemany(command, data)
    else:
      self.pprint('Non-fatal error: Attemtped to run Zeomine.exm() without data')

  # Commit DB data
  def com(self):
    self.db.commit()

  # Execute a DB command, and then commit it
  def excom(self, command, data = False):
    self.ex(command, data)
    self.com()

  # Execute many DB commands, and then commit them
  def exmcom(self, command, data = False):
    self.exm(command, data)
    self.com()

  ##############################################################################
  # Core functions
  ##############################################################################

  ## Primary Run Function
  #
  # All settings go through the CLI parameters or the conf file. Nothing is 
  # passed to this function directly.
  def run(self):
    # Generate metadata
    self.generate_metadata()

    # Load the config file
    self.load_config(self.settings['config_path'])

    # Load and setup the database
    self.initiate()

    # Load any previous state data from plugins
    self.load_previous_state()

    # Crawl the targeted domain(s)
    self.crawl()
    
    # Evaluate collected data
    self.evaluate_data()

    # If we have a alert recommendation, run the alert function
    self.alert()

    # Generate reports and save data
    self.report()
    
    # Run shutdown actions (clean up/save plugin data, etc.)
    self.shutdown()
    
  ## Load Configuration Files
  #
  # This will load the configuration files and specify which plugins to load
  def load_config(self, config_path):
    # Load each config item in the list. Later ones will overwrite earlier ones.
    # Since the log file settings are in flux, we invalidate logging by setting
    # to a high number.
    for conf in config_path:
      # Absolute UNIX path
      if conf[0] == '/':
        path = os.path.abspath(conf)
      # Windows path: C: or D:, etc.
      elif conf[1] == ':':
        path = os.path.abspath(conf)
      # If not absolute, assume relative to user_data/configs
      else:
        path = os.path.abspath('user_data/configs/' + conf)
      self.pprint('Importing config ' + path, 1, 2)
      if not self.debug_mode:
        try:
          self.load_config_file(path)
        except:
          self.pprint("Failed to import " + path, 0, 2)
      else:
        self.load_config_file(path)
      

    # Debug: print settings and configs
    self.pprint('Settings: ', 2, 2)
    self.pprint(self.settings, 2, 2)
    self.pprint('Config: ', 2, 2)
    for a in self.conf:
      for b in self.conf[a]:
        self.pprint(a + ' - ' + b, 2, 2)
        self.pprint(self.conf[a][b], 2, 2)

    # Check we have the crawler. If not, cancel loading Zeomine
    if self.conf['crawler']:
      # Load the crawler
      self.pprint("Loading crawler ", 1, 1)
      crawler_bases = {"core": "core.crawlers", "sample": "samples", "user": "user_data.crawlers"}
      if not self.debug_mode:
        try:
          self.load_components('crawler', self.conf['crawler'], crawler_bases)
        except:
          self.pprint("Crawler could not be imported, most likely due to missing configuration items", 0)
          exit()
      else:
        self.load_components('crawler', self.conf['crawler'], crawler_bases)
      # Load the plugins
      for plug in sorted(self.conf['plugins'].keys()):
        if plug != plug.replace('_', ''):
          p = plug.replace('_', '')
          self.conf['plugins'][p] = self.conf['plugins'][plug]
          del(self.conf['plugins'][plug])
          plug = p
        self.pprint("Loading plugin " + plug, 1, 1)
        plugin_bases = {"core": "core.plugins", "sample": "samples", "user": "user_data.plugins"}
        if not self.debug_mode:
          try:
            self.load_components('plugins', self.conf['plugins'][plug], plugin_bases)
          except:
            self.pprint("Plugin " + plug + " could not be imported, most likely due to missing configuration items", 0)
        else:
          self.load_components('plugins', self.conf['plugins'][plug], plugin_bases)
      
      # Finally, lets call the load_config method for the crawler and each plugin, so they can carry out their startup actions.
      if callable(getattr(self.crawler, 'load_config', False)):
        self.crawler.load_config()
      for plugin in self.plugins:
        if callable(getattr(self.plugins[plugin], 'load_config', False)):
          remote_load = self.plugins[plugin].load_config()
          if remote_load:
            break
          # ~ self.plugins[plugin].load_config()
    else:
      self.pprint('No crawler found', 0, 2)
      exit()

  ## Initiate: Load and setup the database
  #
  # If the database isn't specified, it will instead load the DB in memory.
  # We leave this option open for cases like load testing or simple uptime
  # where we do not necessarily want to record anything.
  def initiate(self):
    # Load the target database
    db_path = ':memory:'
    if self.settings['db_path']:
      db_path = self.settings['user_data']['base'] + self.settings['user_data']['data'] + self.settings['db_path']
    self.db = sqlite3.connect(db_path)
    self.cursor = self.db.cursor()

    # Create the basic data tables if they don't exist
    self.excom('CREATE TABLE IF NOT EXISTS zeomine_instances (uuid text, description text, time_format text, time real)')
    self.excom('CREATE TABLE IF NOT EXISTS domains (domain text, https int, subdomain_of int)')
    self.excom('CREATE TABLE IF NOT EXISTS urls (url text, domain int)')

    # Add the run instance
    self.excom('INSERT INTO zeomine_instances VALUES (?,?,?,?)', (self.data['metadata']['uuid'], self.settings['description'], self.data['metadata']['time_format'], self.data['metadata']['time']))
    self.run_id = self.data['metadata']['uuid']
    
    # Finally, lets call the initiate method for the crawler and each plugin.
    if callable(getattr(self.crawler, 'initiate', False)):
      self.crawler.initiate()
    for plugin in self.plugins:
      if callable(getattr(self.plugins[plugin], 'initiate', False)):
        self.plugins[plugin].initiate()

  ## Load Previous State for running comparisons
  #
  # Load Zeomine's state data first, as some modules may need its info.
  def load_previous_state(self):
    # Now, have the crawler and plugins set themselves up
    if callable(getattr(self.crawler, 'load_previous_state', False)):
      self.crawler.load_previous_state()
    for plugin in self.plugins:
      if callable(getattr(self.plugins[plugin], 'load_previous_state', False)):
        self.plugins[plugin].load_previous_state()

  ## Crawl the targeted domain(s)
  #
  # 
  def crawl(self):
    self.crawler.crawl()

  ## Evaluate Data
  #
  # 
  def evaluate_data(self):
    for plugin in self.plugins:
      if callable(getattr(self.plugins[plugin], 'evaluate_data', False)):
        self.plugins[plugin].evaluate_data()

  ## Send Alerts
  #
  # This is meant to fire only if we have alert data
  def alert(self):
    if self.data['alerts']:
      for plugin in self.plugins:
        if callable(getattr(self.plugins[plugin], 'alert', False)):
          self.plugins[plugin].alert()

  ## Generate Reports and save data
  #
  # 
  def report(self):
    for plugin in self.plugins:
      if callable(getattr(self.plugins[plugin], 'report', False)):
        self.plugins[plugin].report()

  ## Final actions for Zeomine shutdown
  #
  # 
  def shutdown(self):
    # Let plugins run first
    if callable(getattr(self.crawler, 'shutdown', False)):
      self.crawler.shutdown()
    for plugin in self.plugins:
      if callable(getattr(self.plugins[plugin], 'shutdown', False)):
        self.plugins[plugin].shutdown()

    # Close the DB, we are done
    self.db.close()
