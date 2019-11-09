## Null Crawler
#
# Use this in situations where you do not want to crawl anything, and
# only wish to evaluate existing data.
#
class NullCrawler():
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
  # ZSM plugins
  ##############################################################################

  def load_config(self):
    self.z_obj.pprint('Successfully loaded NullCrawler.', 2, 2)

  def crawl(self):
    pass
