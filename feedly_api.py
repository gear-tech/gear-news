import requests
import re

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
    clean_text = re.sub(' +', ' ', summary).replace('\n', '').rstrip()

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
      'preview': self._generate_preview(entry.get('summary', {}).get('content', ''))
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
    return self._fetch(f'mixes/contents', params = params)

  # collect the most engaging articles from the primary feed
  def collect_content(self, label, lifespan, count = 5):
    # retrieve matching collections by label provided
    collections_ids = [c['id'] for c in self.fetch_collections() if label.lower() == c['label'].lower()]

    if not len(collections_ids):
      return {
        'success': False,
        'error': 'No collections matched the label.'
      }
  
    stream_id = collections_ids[0]
    mix_response = self.fetch_feed_mix(stream_id, lifespan, count).get('items', [])

    return {
      'success': True,
      'data': self._remove_duplicates([self._format_entry(entry) for entry in mix_response]),
    }
