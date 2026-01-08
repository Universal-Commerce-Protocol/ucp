#   Copyright 2026 UCP Authors
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.


"""MkDocs hooks for UCP documentation.

This module contains functions that are executed during the MkDocs build
process.
Currently, it includes a hook to copy specs files into the site directory
after the build is complete.
This makes the specs JSON files available in the website and programmatically
accessible.
"""

import logging
import os
import shutil

log = logging.getLogger('mkdocs')


def on_post_build(config):
  """Moves all subdirectories from the spec/ directory to the site directory after the build is complete.

  Args:
      config: The mkdocs config object.
  """

  # Base path for the source directories
  base_src_path = os.path.join(os.getcwd(), 'spec')

  # Check if the parent 'spec' folder exists first
  if not os.path.exists(base_src_path):
    log.warning('Spec source directory not found: %s', base_src_path)
    return

  # Iterate over everything inside 'spec'
  for item in os.listdir(base_src_path):
    src = os.path.join(base_src_path, item)

    # Only copy directories, skipping files like README.md in spec/.
    if os.path.isdir(src):
      dest = os.path.join(config['site_dir'], item)

      # Clean up destination if it already exists to ensure a fresh copy
      if os.path.exists(dest):
        shutil.rmtree(dest)

      shutil.copytree(src, dest)
      log.info('Copied directory %s from %s to %s', item, src, dest)
