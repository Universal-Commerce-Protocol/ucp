#   Copyright 2025 UCP Authors
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
Currently, it includes a hook to copy schema files into the site directory
after the build is complete.
This makes the schema JSON files available in the website and programmatically
accessible at /schemas.
"""

import logging
import os
import shutil

log = logging.getLogger('mkdocs')


def on_post_build(config):
  """Moves all json files from the spec/schemas directory to the site directory after the build is complete.

  Args:
    config: The mkdocs config object.
  """

  src = os.path.join(os.getcwd(), 'spec', 'schemas')
  dest = os.path.join(config['site_dir'], 'schemas')

  if os.path.exists(src):
    if os.path.exists(dest):
      shutil.rmtree(dest)
    shutil.copytree(src, dest)
    log.info('Copied schemas from %s to %s', src, dest)
  else:
    log.warning('Schema source directory not found: %s', src)
