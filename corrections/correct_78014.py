"""Temporary read-only authenticated preflight for the authorized venue correction."""
import json
import os
import base64
import urllib.request
import urllib.error

BASE = 'https://desotocountynews.com'
URL = BASE + '/wp-json/wp/v2/posts/78014?context=edit'

if __name__ == '__main__':
    if os.environ['WORDPRESS_BASE_URL'].rstrip('/') != BASE:
        raise SystemExit('Unexpected WordPress site')
    auth = base64.b64encode((os.environ['WORDPRESS_USERNAME'] + ':' +
                            os.environ['WORDPRESS_APP_PASSWORD']).encode()).decode()
    request = urllib.request.Request(URL, headers={'Authorization': 'Basic ' + auth,
                                                  'User-Agent': 'python-requests/2.32.5',
                                                  'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            post = json.load(response)
    except urllib.error.HTTPError as error:
        body = error.read()
        try:
            failure = json.loads(body)
            print('WordPress preflight failed:', error.code, failure.get('code'), failure.get('message'))
        except ValueError:
            print('Preflight failed:', error.code, 'non-JSON response',
                  'Cloudflare' if b'cloudflare' in body.lower() else 'server denial')
        # Read-only diagnosis; report capability booleans, never account names or credentials.
        diagnostic = urllib.request.Request(BASE + '/wp-json/wp/v2/users/me?context=edit',
                                             headers=dict(request.header_items()))
        try:
            with urllib.request.urlopen(diagnostic, timeout=40) as response:
                user = json.load(response)
            capabilities = user.get('capabilities', {})
            print('ACCOUNT_CAPABILITIES=' + json.dumps({
                'authenticated': bool(user.get('id')),
                'roles': user.get('roles', []),
                'edit_posts': capabilities.get('edit_posts'),
                'edit_others_posts': capabilities.get('edit_others_posts'),
                'edit_published_posts': capabilities.get('edit_published_posts'),
            }))
        except urllib.error.HTTPError as diagnostic_error:
            print('Account capability read failed:', diagnostic_error.code)
        raise SystemExit(1)
    if post['id'] != 78014 or post['status'] != 'publish':
        raise SystemExit('Unexpected post identity/status')
    keys = ['id', 'type', 'status', 'slug', 'link', 'date', 'date_gmt',
            'modified', 'modified_gmt', 'author', 'featured_media', 'categories',
            'tags', 'comment_status', 'ping_status', 'sticky', 'template',
            'format', 'title', 'content', 'excerpt', 'meta']
    snapshot = {key: post[key] for key in keys}
    for key in ['title', 'content', 'excerpt']:
        if not isinstance(snapshot[key].get('raw'), str):
            raise SystemExit('Authenticated raw content unavailable')
    print('RAW_SNAPSHOT=' + json.dumps(snapshot, ensure_ascii=False))
