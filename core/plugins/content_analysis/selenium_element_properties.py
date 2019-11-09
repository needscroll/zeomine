import hashlib
from bs4 import BeautifulSoup

## Selenium Element properties
#
# Get properties of an element identifed in a Selenium Browser.
# This should be listed as a 

class SeleniumElementProperties():
  ##############################################################################
  # Plugin Settings
  ##############################################################################
  
  # Define the parent Zeomine object so we can call its functions and access its 
  # data. Set this in load_config
  z_obj = None

  # Define the parent crawler object
  parent_obj = None

  # Settings dict
  settings = {}
  settings['selectors'] = {}

  # Local data dict
  data = {}
  data['cache'] = {}

  ##############################################################################
  # Helper Functions
  ##############################################################################

  # Get the database id for an element, searching by hash. If the hash isn't found, add to DB
  def get_element_id(self, hsh, string, urlid):
    d = self.z_obj.fetchone('select rowid from selenium_element where item_hash=? and url=? and zeomine_instance=?', (hsh,urlid,self.z_obj.run_id))
    if d:
      return d[0]
    else:
      self.z_obj.ex('insert into selenium_element values (?,?,?,?)',(self.z_obj.run_id,urlid,hsh,string,))
      self.data['cache'][hsh] = self.z_obj.cursor.lastrowid
      return self.z_obj.cursor.lastrowid

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
    self.z_obj.pprint('Successfully loaded SeleniumElementProperties.', 2, 2)

  ## Initiate Plugin
  #
  # 
  def initiate(self):
    # Create the data table if it doesn't exist yet
    self.z_obj.excom('CREATE TABLE IF NOT EXISTS selenium_element (zeomine_instance text, url int, item_hash text, item_text text)')
    self.z_obj.excom('CREATE TABLE IF NOT EXISTS selenium_element_data (zeomine_instance text, url int, item_id int, selector text, property_name text, property_value text)')

  ##############################################################################
  # Core Crawler - Selenium plugins
  ##############################################################################

  ## Core Selenium Crawler callback
  #
  # 
  def core_crawler_selenium(self, current_url, current_url_id):
    for selector in self.settings['selectors']:
      i = self.parent_obj.browser.find_elements_by_css_selector(selector)
      for item in i:
        # Generate the hash and get the item ID first
        item_text = item.get_attribute('outerHTML')
        b = item_text.encode()
        h = hashlib.sha256(b).hexdigest()
        item_id = self.get_element_id(h, item_text, current_url_id)
        for prop in self.settings['selectors'][selector]:
          if prop == 'size.height':
            prop_data = item.size['height']
          elif prop == 'size.width':
            prop_data = item.size['width']
          elif prop == 'size.area':
            prop_data = item.size['height'] * item.size['width']
          elif prop == 'location.x':
            prop_data = item.location['x']
          elif prop == 'location.y':
            prop_data = item.location['y']
          else:
            prop_data = item.get_attribute(prop)
          add = (self.z_obj.run_id, current_url_id, item_id, selector, prop, prop_data)
          self.z_obj.ex('insert into selenium_element_data values (?,?,?,?,?,?)', add)
    self.z_obj.com()
