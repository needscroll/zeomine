import importlib
import json
import requests
import time

## Remote Configuration
#
class RemoteConf():
  ##############################################################################
  # Plugin Settings
  ##############################################################################
  
  # Define the parent ZSM object so we can call its functions and access its 
  # data. Set this in load_config
  z_obj = None
  
  # Settings dict
  settings = {}
  settings['cache'] = {}
  settings['cache']['cache_conf'] = False
  settings['cache']['cache_expire'] = 86400
  settings['cache']['cache_filename'] = 'conf_cache.json'

  settings['conf_url'] = ''
  settings['api_key'] = ''

  settings['auth'] = {}
  settings['auth']['location'] = ''
  settings['auth']['name'] = ''
  settings['auth']['pass'] = ''

  # Local data dict
  data = {}
  data['remote_conf_loaded'] = False
  data['auth'] = {}
  data['cache_time'] = False
  data['remote_donf'] = {}

  ##############################################################################
  # Helper Functions
  ##############################################################################

  # This is no longer used, but for cookie authentication, it works.
  # We are holding on to it in case this is needed as a starting point for v3.
  # ~ def drupal_login(self):
    # ~ login = {}
    # ~ login['name'] = self.settings['auth']['name']
    # ~ login['pass'] = self.settings['auth']['pass']
    # ~ l = json.dumps(login)

    # ~ req = requests.post(self.settings['auth']['location'], data=l)

    # ~ self.data['auth']['head'] = {}
    # ~ self.data['auth']['cookie'] = {}
    # ~ if req.status_code == 200:
      # ~ r = json.loads(req.text)
      # ~ self.data['auth']['head']['X-CSRF-Token'] = r['csrf_token']
      # ~ self.data['auth']['head']['Accept'] = 'application/json'
      # ~ self.data['auth']['head']['Content-Type'] = 'application/json'
      # ~ self.data['auth']['cookie'] = req.cookies.get_dict()
      # ~ return True
    # ~ else:
      # ~ return False
    

  ##############################################################################
  # ZSM plugins
  ##############################################################################

  ## Add configs to this module from parent object
  #
  def load_config(self):
    if not self.data['remote_conf_loaded']:
      # Like most plugins, load the known config first
      if self.__class__.__name__ in self.z_obj.conf['plugins'] and self.z_obj.conf['plugins'][self.__class__.__name__]:
        conf = self.z_obj.conf['plugins'][self.__class__.__name__]['settings']
        for section in conf:
          if isinstance(conf[section], dict):
            for subsection in conf[section]:
              if section in self.settings and subsection in self.settings[section]:
                self.settings[section][subsection] = conf[section][subsection]
          # If not a dict, assume the section is a single property to set.
          else:
            if section in self.settings:
              self.settings[section] = conf[section]
      # Get the settings data, and apply it to the parent ZSM object
      remote_conf = {}
      if self.settings['cache']['cache_conf']:
        try:
          with open(self.z_obj.settings['user_data']['data'] + settings['cache']['cache_filename'], 'r') as f:
            cache_data = json.load(f)
            if cache_data['time'] + settings['cache']['cache_expire'] > time.time():
              remote_conf = cache_data['remote_conf']
            else:
              pass
        except:
          pass
      
      # Get the config from the site if we didn't get any remote data
      if not remote_conf:
        rc = requests.get(self.settings['conf_url'] + '?_format=json&api-key=' + self.settings['api_key'])
        if rc.status_code == 200:
          remote_conf = json.loads(rc.text)
        else:
          self.z_obj.pprint("REmoteConf failed, authentication info given below:",0)
          self.z_obj.pprint(rc.status_code,0)
          self.z_obj.pprint(rc.text,0)
          # We are going to fail as we could not pull down the config, so stop the crawler now
          self.z_obj.shutdown()
          exit()
      
      if self.settings['cache']['cache_conf']:
        with open(self.z_obj.settings['user_data']['data'] + settings['cache']['cache_filename'], 'w') as f:
          if not self.settings['cache_time']:
            self.settings['cache_time'] = time.time()
          cache_data = {'time': self.settings['cache_time'],'remote_conf': remote_conf}
          write_data = json.dumps(cache_data)
          f.write(write_data)
      
      # Finally, apply the found data and re-run the load_config function for ZSM, but exclude RemoteConf
      self.data['remote_conf_loaded'] = True
      for setting in remote_conf['settings']:
        self.z_obj.settings[setting] = remote_conf['settings'][setting]
      for conf in remote_conf['conf']:
        if conf == 'plugins':
          for component in remote_conf['conf'][conf]:
            self.z_obj.conf[conf][component] = remote_conf['conf'][conf][component]
        else:
          self.z_obj.conf[conf] = remote_conf['conf'][conf]          
          
      # Check we have the crawler. If not, cancel loading Zeomine
      if self.z_obj.conf['crawler']:
        # Load the crawler
        self.z_obj.pprint("Loading crawler ", 1, 1)
        crawler_bases = {"core": "core.crawlers", "sample": "samples", "user": "user_data.crawlers"}
        if not self.z_obj.debug_mode:
          try:
            self.load_components('crawler', self.z_obj.conf['crawler'], crawler_bases)
          except:
            self.z_obj.pprint("Crawler could not be imported, most likely due to missing configuration items", 0)
            exit()
        else:
          self.z_obj.load_components('crawler', self.z_obj.conf['crawler'], crawler_bases)
        # Load the plugins
        for plug in self.z_obj.conf['plugins']:
          self.z_obj.pprint("Loading plugin " + plug, 1, 1)
          plugin_bases = {"core": "core.plugins", "sample": "samples", "user": "user_data.plugins"}
          if not self.z_obj.debug_mode:
            try:
              self.z_obj.load_components('plugins', self.z_obj.conf['plugins'][plug], plugin_bases)
            except:
              self.z_obj.pprint("Plugin " + plug + " could not be imported, most likely due to missing configuration items", 0)
          else:
            self.z_obj.load_components('plugins', self.z_obj.conf['plugins'][plug], plugin_bases)
        
        # Call the load_config method for the crawler.
        if callable(getattr(self.z_obj.crawler, 'load_config', False)):
          self.z_obj.crawler.load_config()
        # ~ for plugin in self.plugins:
          # ~ if callable(getattr(self.z_obj.plugins[plugin], 'load_config', False)):
            # ~ self.z_obj.plugins[plugin].load_config()
      else:
        self.pprint('No crawler found', 0, 2)
        exit()
      
      # Load the plugins, but not ourselves
      for plug in self.z_obj.conf['plugins']:
        if self.z_obj.conf['plugins'][plug]['class'] != 'RemoteConf':
          self.z_obj.pprint("Loading plugin " + plug, 1, 1)
          plugin_bases = {"core": "core.plugins", "sample": "samples", "user": "user_data.plugins"}
          p = self.z_obj.conf['plugins'][plug]
          c = self.z_obj.conf['plugins'][plug]['class']
          m = importlib.import_module(plugin_bases[p['type']] + '.' + p['module'])
          plugin = getattr(m,c)
          # Check to see if we already added this plugin
          chk = []
          for plu in self.z_obj.plugins:
            chk.append(str(plu.__class__))
          if str(c) not in chk:
            # We can add this plugin. Also, set the z_obj
            self.z_obj.plugins[c] = plugin()
            self.z_obj.plugins[c].z_obj = self.z_obj

      # Now call the load_config method for each plugin, so they can carry out their startup actions.
      for plugin in self.z_obj.plugins:
        if callable(getattr(self.z_obj.plugins[plugin], 'load_config', False)):
          self.z_obj.plugins[plugin].load_config()
      
      # Finally, return "True" as we are noting this is a remote loader.
      return True
