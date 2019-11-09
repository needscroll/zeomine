## Sample Crawler
#
class SampleCrawler():
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
  # ZSM plugins
  ##############################################################################

  def crawl(self):
    self.z_obj.pprint('Successfully loaded SampleCrawler.', 0)
