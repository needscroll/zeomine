import hashlib
import img2pdf
from wand.image import Image,Color
from bs4 import BeautifulSoup
from pathlib import Path

## Selenium Screencap
#
# Screencaps pages via Selenium Browser
class SeleniumScreencap():
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
  # Image path: This is relative to the user data folder. Add a trailing slash if you are naming a directory.
  settings['image_path'] = 'images/'
  # The selector for capturing a screenshot. This is a key-value dict, with the key being a label for
  # the image, and the value being the selector
  settings['selectors'] = {} #{'body': 'body'}
  # Force a particular screen width, in pixels
  settings['screen_width'] = 1280
  # By default, screenshots are taken only if they do not exist. This will
  # force re-taking a screenshot.
  settings['force_screenshot'] = False
  #TODO add include/exclude logic
  # Include: Only items meeting these rules will be included
  # Exclude: Any items meeting these rules will be ecluded
  # Both: Items must both included, and not excluded.
  settings['include'] = {}
  settings['exclude'] = {}
  
  # png or pdf
  settings['file_type'] = 'png'

  # Local data dict
  data = {}
  data['cache'] = {}

  ##############################################################################
  # Helper Functions
  ##############################################################################

  def removeAlpha(self, image_path):
    ok = False       
    with Image(filename=image_path) as img:
      alpha = img.alpha_channel
      if not alpha:
        ok = True
        return ok
      try:
        img.alpha_channel = 'remove' #close alpha channel   
        img.background_color = Color('white')        
        img.save(filename=image_path)
        ok = True
      except:
        ok = False
    return ok

  def take_screenshot(self, current_url, current_url_id, path, fname):
    if self.settings['file_type'] == 'png':
      return self.parent_obj.browser.get_screenshot_as_png()
    elif  self.settings['file_type'] == 'pdf':
      fname_png = fname.replace(self.settings['file_type'], 'png')
      # TODO return a PDF
      img = self.parent_obj.browser.get_screenshot_as_png()
      with open(path + fname_png, 'wb') as f:
        f.write(img)
      if self.removeAlpha(path + fname_png):
        pdf = img2pdf.convert(path + fname_png)
        return pdf
      return img

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
    self.z_obj.pprint('Successfully loaded SeleniumScreencap.', 2, 2)

  ## Initiate Plugin
  #
  # 
  def initiate(self):
    # Create the data table if it doesn't exist yet
    self.z_obj.excom('CREATE TABLE IF NOT EXISTS selenium_screencap (zeomine_instance text, url int, screencap_file text)')
    # TODO create directories if they do not exist
    self.z_obj.pprint('TODO add directory creation for SeleniumScreencap.', 0, 0)

  ##############################################################################
  # Core Crawler plugins
  ##############################################################################

  ## Core Selenium Crawler callback
  #
  # 
  def core_crawler_selenium(self, current_url, current_url_id):
    for s in self.settings['selectors']:
      #Screencap
      items = self.parent_obj.browser.find_elements_by_css_selector(self.settings['selectors'][s])
      # We are expecting a single-item list
      for item in items:
        path = self.z_obj.settings['user_data']['base'] + self.z_obj.settings['user_data']['data'] + self.settings['image_path']
        fname = s + '_' + str(current_url_id) + '.' + self.settings['file_type']
        imgpath = Path(path+fname)
        if not imgpath.is_file() or self.settings['force_screenshot']:
          # Get heights
          h = round(item.size['height'])
          w = item.size['width']
          if self.settings['screen_width']:
            self.parent_obj.browser.set_window_size(self.settings['screen_width'],h)
          else:
            self.parent_obj.browser.set_window_size(w,h)
          self.z_obj.pprint('start screencap', 2)
          screencap = self.take_screenshot(current_url, current_url_id, path, fname)
          #~ item.screenshot(path + fname)
          self.z_obj.pprint(self.settings['file_type'] + ' captured', 2)
          with open(path + fname, 'wb') as f:
            f.write(screencap)
          self.z_obj.pprint('end screencap', 2)
          add = (self.z_obj.run_id, current_url_id, self.settings['image_path'] + fname)
          self.z_obj.excom('insert into selenium_screencap values (?,?,?)', add)
          self.z_obj.pprint('Screenshot: ' + self.settings['image_path'] + fname, 1)
        else:
          self.z_obj.pprint('Screenshot already taken.', 1)
  
  ## "Is Crawled" callback
  #
  # True: Screenshot already taken, do not re-take
  # False: Screenshot not taken, OR screenshot should be re-taken
  def check_crawled(self,url, url_id):
    for s in self.settings['selectors']:
      path = self.z_obj.settings['user_data']['base'] + self.z_obj.settings['user_data']['data'] + self.settings['image_path']
      fname = s + '_' + str(url_id) + '.' + self.settings['file_type']
      imgpath = Path(path+fname)
      # 'force_screenshot' forces the URL to be re-crawled and overwritten
      if not imgpath.is_file() or self.settings['force_screenshot']:
        return False
      else:
        return True
