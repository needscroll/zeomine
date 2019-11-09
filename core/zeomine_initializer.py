import time
from core.zeomine import Zeomine

# Zeomine Python class
class ZeomineInitializer():

  settings = {}
  settings['config_path'] = ''
  settings['repeat_count'] = 0
  settings['repeat_time'] = 0
  settings['debug'] = False

  # Init function
  def __init__(self, config_path, settings = {}):
    self.settings['config_path'] = config_path
    if 'repeat_count' in settings:
      self.settings['repeat_count'] = settings['repeat_count']
    if 'repeat_time' in settings:
      self.settings['repeat_time'] = settings['repeat_time']
    if 'debug' in settings:
      self.settings['debug'] = settings['debug']

  # Start and run a Zeomine instance
  def run(self):
    repeats = 0
    if self.settings['config_path'] and isinstance(self.settings['config_path'], list):
      next_run_time = 0
      while repeats <= self.settings['repeat_count']:
        if time.time() > next_run_time:
          next_run_time = time.time() + self.settings['repeat_time']
          if self.settings['debug']:
            zeomine = Zeomine(self.settings['config_path'], self.settings['debug'])
            zeomine.run()
            repeats += 1
          else:
            try:
              zeomine = Zeomine(self.settings['config_path'], self.settings['debug'])
              zeomine.run()
              repeats += 1
            except:
              repeats += 1
        if repeats < self.settings['repeat_count']:
          time.sleep(0.5)
