"""Temporary read-only identification of the existing managed publisher account.

No WordPress post reads or mutations. Credentials remain inside the Actions runner.
"""
import base64
import json
import os
import urllib.request

BASE = 'https://desotocountynews.com'

if __name__ == '__main__':
    if os.environ['WORDPRESS_BASE_URL'].rstrip('/') != BASE:
        raise SystemExit('Unexpected WordPress site')
    auth = base64.b64encode((os.environ['WORDPRESS_USERNAME'] + ':' +
                            os.environ['WORDPRESS_APP_PASSWORD']).encode()).decode()
    request = urllib.request.Request(
        BASE + '/wp-json/wp/v2/users/me?context=edit',
        headers={'Authorization': 'Basic ' + auth,
                 'User-Agent': 'python-requests/2.32.5', 'Accept': 'application/json'})
    with urllib.request.urlopen(request, timeout=40) as response:
        user = json.load(response)
    print('ACCOUNT_IDENTITY=' + json.dumps({
        key: user.get(key) for key in ['id', 'username', 'name', 'slug', 'roles']
    }, ensure_ascii=False))
