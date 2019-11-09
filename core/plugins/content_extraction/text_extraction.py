from bs4 import BeautifulSoup

## Text Extraction
#
# Extracts Text from tags based on selector.

class TextExtraction():
  ##############################################################################
  # Plugin Settings
  ##############################################################################
  
  # Define the parent Zeomine object so we can call its functions and access its 
  # data. Set this in load_config
  z_obj = None
  
  # Settings dict
  settings = {}

  # run_id is the run ID of the Zeomine instance you want to perform the 
  # analysis on. Set to the UUID, or 'current' to get the current run.
  settings['run_id'] = 'current'

  ## Selectors
  #
  # Provide a list of CSS selectors for extracting data.
  settings['selectors'] = ['h1', 'h2']

  # Local data dict
  data = {}

  ##############################################################################
  # Helper Functions
  ##############################################################################

  def get_text(self, url_id, doc):
    parse = BeautifulSoup(doc, 'html.parser')
    for selector in self.settings['selectors']:
      for item in parse.select(selector):
        for s in item.stripped_strings:
          st = str(repr(s))
          self.z_obj.ex('INSERT INTO text_extraction VALUES (?,?,?,?)', (self.z_obj.run_id, url_id, selector, st))
      

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
    self.z_obj.pprint('Successfully loaded TextExtraction.', 2, 2)

  ## Initiate Plugin
  #
  # 
  def initiate(self):
    # Create the data table if it doesn't exist yet
    self.z_obj.excom('CREATE TABLE IF NOT EXISTS text_extraction (zeomine_instance text, url int, selector text, extracted_text text)')
    if self.settings['run_id'] == 'current':
      self.settings['run_id'] = self.z_obj.run_id

  ## Evaluate Data
  #
  # 
  def evaluate_data(self):
    doclist = self.z_obj.fetchall('select url,response_text,type from crawler_req_text inner join crawler_basic_data on crawler_req_text.crawl_data=crawler_basic_data.rowid where crawler_req_text.zeomine_instance=?',(str(self.z_obj.run_id),))
    for doc_data in doclist:
      if doc_data[2] == 'internal':
        self.get_text(doc_data[0],doc_data[1])
    #Save the data aftter we are done extracting
    self.z_obj.com()
