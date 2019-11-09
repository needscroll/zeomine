from bs4 import BeautifulSoup

## Tag Data Extraction
#
# Extracts data attributes from tags based on selector.

class TagDataExtraction():
  ##############################################################################
  # Plugin Settings
  ##############################################################################
  
  # Define the parent ZSM object so we can call its functions and access its 
  # data. Set this in load_config
  z_obj = None
  
  # Settings dict
  settings = {}
  
  # Tag data to extract. The key is a CSS selector, and the value is
  # an array of tag data to select.
  # 
  # Example:
  # settings['tags']['a'] = ['class']
  settings['tags'] = {}
  
  # run_id is the run ID of the Zeomine instance you want to perform the 
  # analysis on. Set to the UUID, or 'current' to get the current run.
  settings['run_id'] = 'current'

  # Local data dict
  data = {}

  ##############################################################################
  # Helper Functions
  ##############################################################################

  def get_text(self, url_id, doc):
    parse = BeautifulSoup(doc, 'html.parser')
    add = []
    for selector in self.settings['tags']:
      search = parse.select(selector)
      for item in search:
        for dat in self.settings['tags'][selector]:
          data = item.get(dat)
          if data:
            data_str = ''
            if isinstance(data, str):
              data_str = data
            else:
              data_str = ' '.join(data)
            add_info = (self.z_obj.run_id,)
            add_info = add_info + (url_id,)
            add_info = add_info + (selector,)
            add_info = add_info + (data_str,)
            add.append(add_info)
    # Add all of the found items to the database
    self.z_obj.exm('INSERT INTO tag_data_extraction VALUES (?,?,?,?)', add)

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
    self.z_obj.pprint('Successfully loaded TagDataExtraction.', 2, 2)

  ## Initiate plugin
  #
  # 
  def initiate(self):
    # Create the data table if it doesn't exist yet
    self.z_obj.excom('CREATE TABLE IF NOT EXISTS tag_data_extraction (zeomine_instance text, url int, selector text, tag_data text)')
    if self.settings['run_id'] == 'current':
      self.settings['run_id'] = self.z_obj.run_id

  ## Evaluate Data
  #
  # 
  def evaluate_data(self):
    # Create the data table if it doesn't exist yet
    doclist = self.z_obj.fetchall('select url,response_text,type from crawler_req_text inner join crawler_basic_data on crawler_req_text.crawl_data=crawler_basic_data.rowid where crawler_req_text.zeomine_instance=?',(str(self.z_obj.run_id),))
    for doc_data in doclist:
      if doc_data[2] == 'internal':
        self.get_text(doc_data[0],doc_data[1])
    #Save the data aftter we are done extracting
    self.z_obj.com()
