import argparse
import time
from core.zeomine_initializer import ZeomineInitializer

# Handle arguments
parser = argparse.ArgumentParser(description="Inititates Zeomine Server Monitor")
parser.add_argument('--conf', help='Path to config file in YAML format, relative to user_data/configs, or an absolute path. May be a comma-separated list of configuration files.')
parser.add_argument('--repeat_count', type=int, help='Repeat a specified number of times. Defaults to 0 (run once).')
parser.add_argument('--repeat_time', type=float, help='Time to wait until the next run. If the first run goes over this time, the next run will wait until it is finished. Defaults to 0 (run immediately).')
parser.add_argument('--debug', type=int, help='Bypasses certain try/except blocks to enable debugging. Can be 1 or 0')

args = parser.parse_args()

# Get configuration list
config_path = args.conf.split(',')
settings = {}
settings['repeat_count'] = args.repeat_count if args.repeat_count else 0
settings['repeat_time'] = args.repeat_time if args.repeat_time else 0
settings['debug'] = True if args.debug else False

z = ZeomineInitializer(config_path, settings)
z.run()
