# +--------------------------------------------------------------------+
# | PythonAnywhere WSGI Configuration for JustRelax Project            |
# | Host: vaibhavxrathod.pythonanywhere.com                           |
# +--------------------------------------------------------------------+

import os
import sys

# 1. Path to your project folder on PythonAnywhere
path = '/home/vaibhavxrathod/justrelax'
if path not in sys.path:
    sys.path.append(path)

# 2. Set environment variables
os.environ['DJANGO_SETTINGS_MODULE'] = 'core.settings'

# 3. Import WSGI Application handler
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
