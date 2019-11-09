import json
import requests

## Spectra Reporter
#
# Send data to a Spectra Server for storage and sharing. 
#
# Use SpectraLoader to retrieve data from a server.
#
class SpectraReporter():
  ##############################################################################
  # Plugin Settings
  ##############################################################################

  # Define the parent ZSM object so we can call its functions and access its 
  # data. Set this in load_config
  z_obj = None

  # Settings dict
  settings = {}
  
  # When to send the data
  #
  # May be 'report' or 'shutdown', and invalid entries will not report.
  settings['send_function'] = 'report'

  # Endpoint of the server
  settings['server'] = {}
  settings['server']['endpoint'] = ''
  settings['server']['api_key'] = ''

  # Queries for getting spectra data
  # List of dicts
  # Example:
  # query = {'query': 'select selector,extracted_text from text_extraction where selector="h1" and zeomine_instance=uuid;'}
  # query['spectra'] = {}
  # query['spectra']['actor'] = {'name': 'mydomain.com', 'type': 'website'}
  # query['spectra']['action'] = {'name': 'has_extracted_text'}
  # query['spectra']['object'] = {'name': {'__variable':0}, 'type':'selector'}
  # query['spectra']['context'] = {'name': 'Zeomine Instance Name', 'type':'zeomine_instance'}
  # query['spectra']['data'] = {'type': 'extracted_text', 'data':{'selector':{'__variable':0},'text':{'__variable':1}}}
  # You may add a plugin for data processing. It must implement prepare_spectra_data(), and be set up in the Zeomine instance
  # query['plugin'] = 'SomeSpectraPlugin'
  # The add the query to the list:
  # settings['queries'].append(query)
  settings['queries'] = []
  

  # Plugins for handling data
  plugins = {}

  # Local data dict
  data = {}

  ##############################################################################
  # Helper Functions
  ##############################################################################

  def create_spectra_object(self, obj, data):
    ret = {}
    if not isinstance(obj, dict):
      return str(obj)
    for key in obj:
      if isinstance(obj[key], dict) and len(obj[key]) == 1 and '__variable' in obj[key] and obj[key]['__variable'] < len(data):
        ret[key] = data[obj[key]['__variable']]
      elif isinstance(obj[key], dict):
        ret[key] = self.create_spectra_object(obj[key], data)
      elif isinstance(obj[key], list):
        ret[key] = []
        for item in obj[key]:
          ret[key].append(self.create_spectra_object(item, data))
      else:
        ret[key] = str(obj[key])
    return ret

  def prepare_data(self, query, data):
    ret = []
    if 'plugin' in query:
      plugin = query['plugin']
      if plugin in self.plugins:
        if callable(getattr(self.plugins[plugin], 'prepare_spectra_data', False)):
          spectra_objects = self.plugins[plugin].prepare_spectra_data(query, data)
          if spectra_objects:
            for so in spectra_objects:
              ret.append(so)
          else:
            return []
    else:
      for d in data:
        spectra_object = self.create_spectra_object(query['spectra'], d)
        ret.append(spectra_object)
      
    return ret

  def post_spectra_data(self):
    # Run through each query item
    for query in self.settings['queries']:
      # Do the query
      if '[current]' in query['query']:
        query['query'] = query['query'].replace('[current]', self.z_obj.run_id)
      data = self.z_obj.fetchall(query['query'])
      spectra_objects = self.prepare_data(query, data)
      self.z_obj.pprint('Sending Spectra Objects',2)
      for so in spectra_objects:
        self.z_obj.pprint(so,2)
        head = {'api-key': self.settings['server']['api_key']}
        head['Content-Type'] = 'application/json'
        spectraj = json.dumps(so)
        req = requests.post(self.settings['server']['endpoint'], data=spectraj, headers=head)
        self.z_obj.pprint(req.status_code,2)
        self.z_obj.pprint(req.text,2)

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
    self.z_obj.pprint('Successfully loaded SpectraListData.', 2, 2)

  ## Initiate Plugin
  #
  # 
  def initiate(self):
    # Set up the plugins
    if self.settings['queries']:
      for q in self.settings['queries']:
        if 'plugin' in q and q['plugin'] in self.z_obj.plugins:
          self.plugins[q['plugin']] = self.z_obj.plugins[q['plugin']]
          self.plugins[q['plugin']].parent_obj = self

  ## Generate Reports and save data
  #
  # 
  def report(self):
    if self.settings['send_function'] == 'report':
      self.post_spectra_data()
  
  ## Final actions for Zeomine shutdown
  #
  # 
  def shutdown(self):
    if self.settings['send_function'] == 'shutdown':
      self.post_spectra_data()
