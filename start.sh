#!/bin/bash
cd /www/wwwroot/volcanocross.com
export SUPABASE_URL="https://xehoqrboglykebqvovgj.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="您的实际密钥"
export FLASK_SECRET_KEY="您的Flask密钥"
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:application 