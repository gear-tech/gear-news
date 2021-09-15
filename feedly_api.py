import requests
import re
import time

class FeedlyApi:
  def __init__(self, access_token, refresh_token):
    self.access_token = access_token
    self.refresh_token = refresh_token
    self.active = False

    # attempt to connect to the API and abort on failure
    if self.fetch_profile().get('id') is None:
      return
    
    self.active = True
  
  def _fetch(self, endpoint, params = {}):
    headers = {'Authorization': f'Bearer {self.access_token}'}
    return requests.get(f'https://cloud.feedly.com/v3/{endpoint}', headers = headers, params = params).json()
  
  def _generate_title(self, title):
    return re.sub(' +', ' ', title).replace('\n', '').rstrip()

  def _generate_preview(self, summary):
    tag_cleaner = re.compile('<.*?>')
    clean_text = re.sub(tag_cleaner, '', re.sub(' +', ' ', summary)).replace('\n', '').rstrip()

    if not clean_text:
      return ''

    return ' '.join(clean_text.split(' ')[:50]) + '...'


  def _format_entry(self, entry):
    return {
      'url': entry.get('alternate', [{}])[0].get('href', ''),
      'tags': [item['label'] for item in entry.get('commonTopics', [])],
      'title': self._generate_title(entry.get('title', '')),
      'thumbnail': entry.get('visual', {}).get('url', ''),
      'source': entry.get('origin', {}).get('title', ''),
      'sourceUrl': entry.get('origin', {}).get('htmlUrl', ''),
      'preview': self._generate_preview(entry.get('summary', {}).get('content', '')),
      'published': round(entry.get('published', 1000) / 1000),
    }

  def _remove_duplicates(self, entries):
    result = []

    for entry in entries:
      if entry['title'] not in [item['title'] for item in result]:
        result.append(entry)

    return result

  # fetch API user's profile
  def fetch_profile(self):
    return self._fetch('profile')

  # identify a list of feeds available on the account
  def fetch_collections(self):
    return self._fetch('collections')

  # fetch the most engaging articles from the feed
  def fetch_feed_mix(self, stream_id, lifespan, count = 5):
    params = {
      'streamId': stream_id,
      'count': count,
      'hours': lifespan,
      'backfill': True,
      'locale': 'en',
    }
    return self._fetch('mixes/contents', params = params)

  def fetch_stream(self, stream_id, lifespan, count = 5):
    params = {
      'streamId': stream_id,
      'count': count,
      'ranked': 'engagement',
      'importantOnly': True,
      # calculate the last update time
      'newerThan': round(time.time() - lifespan * 60 * 60),
    }

    return self._fetch('streams/contents', params = params)

  # collect the most engaging articles from the specified feed
  def collect_content(self, fetch_fn, label, lifespan, count = 5):
    # retrieve matching collections by label provided
    collections_ids = [c['id'] for c in self.fetch_collections() if label.lower() == c['label'].lower()]

    if not len(collections_ids):
      return {
        'success': False,
        'error': 'No collections matched the label.'
      }
  
    stream_id = collections_ids[0]
    items = fetch_fn(stream_id, lifespan, count = count).get('items', [])

    return {
      'success': True,
      'data': self._remove_duplicates([self._format_entry(entry) for entry in items]),
    }
