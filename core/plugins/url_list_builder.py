## Sample Plugin
#
class URLListBuilder():
  ##############################################################################
  # Plugin Settings
  ##############################################################################
  
  # Define the parent ZSM object so we can call its functions and access its 
  # data. Set this in load_config
  z_obj = None
  
  # Settings dict
  settings = {}
  # Variables:
  # 
  # This is a dict with key as arible name, and value is either a dict with a
  # 'min' and 'max' parameter, or a list of items to insert for the array.
  settings['variables'] = {}
  # Base URLs are a list of URLs with variables in the format 
  # [variable_name] inserted into the URL.
  settings['base_urls'] = []
  
  # TODO have a way to set this per URL set
  settings['url_depth'] = 1

  # Local data dict
  data = {}

  ##############################################################################
  # Helper Functions
  ##############################################################################

  ###########
  # Generate URLS
  
  def generate_urls(self):
    ## Generate variable sets
    vrs = {}
    urls = []
    for v in self.settings['variables']:
      vlabel = ''.join(['[',v,']'])
      if isinstance(self.settings['variables'][v], list):
        vrs[vlabel] = self.settings['variables'][v]
      elif isinstance(self.settings['variables'][v], dict) and \
      'min' in self.settings['variables'][v] and 'max' in self.settings['variables'][v]:
        vrs[vlabel] = range(self.settings['variables'][v]['min'], self.settings['variables'][v]['max'] + 1)
    # Perform variable replacement, 'us' are the pre-categorized urls
    us = []
    for b in self.settings['base_urls']:
      add_list = [b]
      done = False
      while not done:
        done = True
        for v in vrs:
          new_list = []
          for item in add_list:
            if v in item:
              done = False
              for i in vrs[v]:
                add = item
                add = add.replace(v, str(i))
                new_list.append(add)
          add_list = new_list
        us = us + add_list
    
    # Determine url types
    if callable(getattr(self.z_obj.crawler, 'get_url_type', False)):
      for u in us:
        typ = self.z_obj.crawler.get_url_type(u)
        urls.append({'url': u, 'type': typ})
      
    return urls

  ##############################################################################
  # Zeomine plugins
  ##############################################################################

  ## Add configs to this module from parent object
  #
  def load_config(self):
    # If we have settings, load them.
    if self.__class__.__name__ in self.z_obj.conf['plugins'] and self.z_obj.conf['plugins'][self.__class__.__name__]:
      conf = self.z_obj.conf['plugins'][self.__class__.__name__]['settings']
      for section in conf:
        if isinstance(conf[section], dict):
          for subsection in conf[section]:
            if section in self.settings:
              self.settings[section][subsection] = conf[section][subsection]
        # If not a dict, assume the section is a single property to set.
        else:
          self.settings[section] = conf[section]
    self.z_obj.pprint('Successfully loaded URLListBuilder.', 2, 2)

  ## Initiate Plugin
  #
  # 
  def initiate(self):
    urls = self.generate_urls()
    for u in urls:
      url = u['url']
      typ = u['type']
      if url not in self.z_obj.crawler.data['urls_to_crawl'][typ]:
        self.z_obj.crawler.data['urls_to_crawl'][typ].append({'url': url, 'depth': self.settings['url_depth']})
