## Word Count
#
class WordCount():
  ##############################################################################
  # Plugin Settings
  ##############################################################################
  
  # Define the parent ZSM object so we can call its functions and access its 
  # data. Set this in load_config
  z_obj = None
  
  # Settings dict
  settings = {}
  
  # The type of report to generate. This is a list with 'run' for an
  # entire Zeomine run, 'url' for a per-url count, or both
  settings['report_type'] = ['run']
  
  # run_id is the run ID of the Zeomine instance you want to perform the 
  # analysis on. Set to the UUID, or 'current' to get the current run.
  settings['run_id'] = 'current'
  
  # The selector from text_extraction, or False if you want to include everything.
  settings['selector'] = False
  
  # List of words to not include in our report.
  settings['blacklist'] = [] # Example: ['a', 'an', 'the']
  
  # List of substrings to remove from found words, usually punctuation
  settings['cleanup_list'] = [':', ';', '--', '?', '&', '.', '!', ',', '"', '”', '“', '‘','’', '(', ')', "'"]
  
  # Minimum length of words to include
  settings['min_length'] = 1
  
  # Limit reporting to a maximum number of words, a minimum fraction, or
  # minimum normalized fraction. Set to False for no limit.
  settings['report_limit'] = {}
  settings['report_limit']['max_words'] = False
  settings['report_limit']['fraction'] = False
  settings['report_limit']['normalized_fraction'] = False

  # Local data dict
  data = {}
  data['word_count'] = {'run': {}, 'url': {}}

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
        substr = str(substr)
        if substr in item:
          return True
      return False

  # Check against blacklist: item does not contain a matching substring
  def in_blacklist(self, item, blacklist):
    if not blacklist:
      return False
    else:
      for substr in blacklist:
        substr = str(substr)
        if substr in item:
          return True
      return False
  
  # Text Cleaner
  def clean_text(self, text):
    ret = []
    #cleanup_list = [':', '-', '?', '&']
    for t in text:
      for c in self.settings['cleanup_list']:
        t = t.replace(c, '')
      if t:
        if len(t) >= self.settings['min_length']:
          if not self.in_blacklist(t.lower(), self.settings['blacklist']):
            ret.append(t)
    return ret

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
    self.z_obj.pprint('Successfully loaded WordCount.', 2, 2)

  ## Initiate Plugin
  #
  # 
  def initiate(self):
    self.z_obj.excom('CREATE TABLE IF NOT EXISTS word_count (zeomine_instance text, url int, word text, count int, fraction float, normalized_fraction float)')
    if self.settings['run_id'] == 'current':
      self.settings['run_id'] = self.z_obj.run_id

  ## Generate Reports and save data
  #
  # 
  def report(self):
    if self.settings['selector']:
      text_data = self.z_obj.fetchall('select url,extracted_text from text_extraction where zeomine_instance=? and selector=?', (self.settings['run_id'],self.settings['selector']))
    else:
      text_data = self.z_obj.fetchall('select url,extracted_text from text_extraction where zeomine_instance=?', (self.settings['run_id'],))
    # Calculate word counts
    for tdata in text_data:
      td = tdata[1].strip("'").split(' ')
      td = self.clean_text(td)
      if 'url' in self.settings['report_type'] and tdata[0] not in self.data['word_count']['url']:
        self.data['word_count']['url'][tdata[0]] = {}
      for t in td:
        tl = t.lower()
        if 'run' in self.settings['report_type']:
          if tl in self.data['word_count']['run']:
            self.data['word_count']['run'][tl] += 1
          else:
            self.data['word_count']['run'][tl] = 1
        if 'url' in self.settings['report_type']:
          if tl in self.data['word_count']['url'][tdata[0]]:
            self.data['word_count']['url'][tdata[0]][tl] += 1
          else:
            self.data['word_count']['url'][tdata[0]][tl] = 1

    # Create reports
    if 'run' in self.settings['report_type']:
      max_word = max(self.data['word_count']['run'], key=self.data['word_count']['run'].get)
      max_word_count = self.data['word_count']['run'][max_word]
      total = sum(self.data['word_count']['run'].values())
      i=0
      for word in sorted(self.data['word_count']['run'], key=self.data['word_count']['run'].get, reverse=True):
        if (not self.settings['report_limit']['max_words'] or i < self.settings['report_limit']['max_words']):
          count = self.data['word_count']['run'][word]
          frac = self.data['word_count']['run'][word] / total
          norm = self.data['word_count']['run'][word] / max_word_count
          if (not self.settings['report_limit']['fraction'] or frac > self.settings['report_limit']['fraction']) and \
          (not self.settings['report_limit']['normalized_fraction'] or norm > self.settings['report_limit']['normalized_fraction']):
            i += 1
            self.z_obj.ex('insert into word_count values (?,0,?,?,?,?)', (self.settings['run_id'],word,count,frac,norm))
      self.z_obj.com()
    if 'url' in self.settings['report_type']:
      for url in self.data['word_count']['url']:
        max_word = max(self.data['word_count']['url'][url], key=self.data['word_count']['url'][url].get)
        max_word_count = self.data['word_count']['url'][url][max_word]
        total = sum(self.data['word_count']['url'][url].values())
        i=0
        for word in sorted(self.data['word_count']['url'][url], key=self.data['word_count']['url'][url].get, reverse=True):
          if (not self.settings['report_limit']['max_words'] or i < self.settings['report_limit']['max_words']):
            count = self.data['word_count']['url'][url][word]
            frac = self.data['word_count']['url'][url][word] / total
            norm = self.data['word_count']['url'][url][word] / max_word_count
            if (not self.settings['report_limit']['fraction'] or frac > self.settings['report_limit']['fraction']) and \
            (not self.settings['report_limit']['normalized_fraction'] or norm > self.settings['report_limit']['normalized_fraction']):
              i += 1
              self.z_obj.ex('insert into word_count values (?,?,?,?,?,?)', (self.settings['run_id'],url,word,count,frac,norm))
        self.z_obj.com()

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
