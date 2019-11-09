import json
import requests

## Spectra List Data
#
# Takes data from SpectraReporter, and prepares it as a single statement for a list.
#
class SpectraListData():
  ##############################################################################
  # Plugin Settings
  ##############################################################################

  # Define the parent ZSM object so we can call its functions and access its 
  # data. Set this in load_config
  z_obj = None
  
  # Parent Sepctra reporter
  parent_obj = None

  # Settings dict
  settings = {}

  # Include only certain columns from the queried data in the list.
  # This is useful when some data only needs to be used for 
  # self.parent_obj.create_spectra_object()
  #
  # Enter a list of column indeces, first is zero. To include only the
  # first and second columns, for exmaple, enter [0,1]
  settings['include'] = []

  # Local data dict
  data = {}

  ##############################################################################
  # Helper Functions
  ##############################################################################

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

  ##############################################################################
  # Additional plugins
  ##############################################################################

  ## Prepare data from Spectra query
  #
  # Take all items in the query, and turn it into single item with a list of data
  #
  def prepare_spectra_data(self, query, data):
    if isinstance(data, list) and len(data) > 0:
      spectra_object = query['spectra'], self.parent_obj.create_spectra_object(query['spectra'], data[0])
      if spectra_object:
        spectra_object = spectra_object[0]
        if 'data' not in spectra_object:
          spectra_object['data'] = {'type': 'default'}
        if not self.settings['include']:
          spectra_object['data']['data'] = data
          return [spectra_object]
        else:
          spectra_object['data']['data'] = []
          for d in data:
            row = []
            for i in self.settings['include']:
              if self.z_obj.debug_mode:
                row.append(d[i])
              else:
                try:
                  row.append(d[i])
                except:
                  pass
            spectra_object['data']['data'].append(row)
          return [spectra_object]
    else:
      self.z_obj.pprint('Invalid data given to SpectraListData. Please provide a non-empty list', 0)
