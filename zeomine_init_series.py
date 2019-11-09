import argparse
import time
import os
import yaml
from core.zeomine_initializer import ZeomineInitializer

# Handle arguments
parser = argparse.ArgumentParser(description="Inititates a series of Zeomine Server Monitor instances")
parser.add_argument('--conf', help='Path to config file in YAML format, relative to user_data/configs, or an absolute path. Only one file is allowed, and must contain a "series" parameter with keys set to zeomine_init parameters.')

args = parser.parse_args()

# Get configuration list
config_path = args.conf
if config_path and isinstance(config_path, str):
  path = ''
  if config_path[0] == '/':
    path = os.path.abspath(conf)
  # Windows path: C: or D:, etc.
  elif config_path[1] == ':':
    path = os.path.abspath(conf)
  # If not absolute, assume relative to user_data/configs
  else:
    path = os.path.abspath('user_data/configs/' + config_path)
  c = {}
  with open(path, 'r') as f:
    # Get the list of configs and applicable settings
    c = yaml.load(f)

  if 'conf_series' in c:
    for conf in c['conf_series']:
      if isinstance(conf, str):
        z = ZeomineInitializer(conf.split(','))
        z.run()
      elif isinstance(conf, dict):
        if 'conf_path' in conf:
          conf_path = conf['conf_path']
          settings = {}
          if 'repeat_count' in settings:
            settings['repeat_count'] = conf['repeat_count']
          if 'repeat_time' in settings:
            settings['repeat_time'] = conf['repeat_time']
          if 'debug' in settings:
            settings['debug'] = conf['debug']
          z = ZeomineInitializer(conf_path.split(','), settings)
          z.run()
