## Sample Plugin
#
class SamplePlugin():
  ##############################################################################
  # Plugin Settings
  ##############################################################################
  
  # Define the parent ZSM object so we can call its functions and access its 
  # data. Set this in load_config
  z_obj = None
  
  # Settings dict
  settings = {}

  # Local data dict
  data = {}

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
    # Run additonal actions specific to your plugin
    self.z_obj.pprint("Successfully loaded SamplePlugin.", 0)

  ## Initiate Plugin
  #
  # 
  def initiate(self):
    pass

  ## Load Previous State for running comparisons
  #
  # 
  def load_previous_state(self):
    pass

  ## Evaluate Data
  #
  # 
  def evaluate_data(self):
    pass

  # Authenticate with remote services
  #
  #
  def authenticate(self):
    pass

  ## Send Alerts
  #
  # 
  def alert(self):
    pass

  ## Generate Reports and save data
  #
  # 
  def report(self):
    pass

  ## Final actions for Zeomine shutdown
  #
  # 
  def shutdown(self):
    pass

  ##############################################################################
  # Core Crawler - Selenium plugins
  ##############################################################################

  ## Core Selenium Crawler callback
  #
  # 
  def core_crawler_selenium(self, current_url):
    pass
