import schedule
import time
from datetime import date
import os
import argparse
from feedly_api import FeedlyApi
from telegram_api import TelegramChannelBotApi

DEFAULT_COUNT = 5
INTRO_NEWS = 'GEAR News Digest'
INTRO_SM = 'GEAR Social Media Digest'

feedly_access_token = os.environ.get('FEEDLY_ACCESS_TOKEN')
feedly_refresh_token = os.environ.get('FEEDLY_REFRESH_TOKEN')
telegram_bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')

if None in (feedly_access_token, feedly_refresh_token, telegram_bot_token):
  print('Missing environmental variables. Aborting.')
  exit()

parser = argparse.ArgumentParser(description='Run GEAR News Telegram Bot digest scheduler.')
parser.add_argument('channel', type=str, help='Telegram channel to send digest to.')
parser.add_argument('news_feed', type=str, help='Feedly Feed label to use for the news digest.')
parser.add_argument('sm_feed', type=str, help='Feedly Feed label to use for the social media digest.')
parser.add_argument('time', type=str, help='Time to publish the digest')
parser.add_argument('freq', type=int, help='Amount of hours between posting the digest')
parser.add_argument('--count', type=int, help='Number of articles to include in the digest.')
parser.add_argument('--force-init', action='store_true', help='Publish a digest upon starting the script.')
args = parser.parse_args()

telegram_channel = args.channel
news_feed_label = args.news_feed
sm_feed_label = args.sm_feed
publish_time = args.time
frequency = args.freq
digest_count = args.count or DEFAULT_COUNT
force_init = args.force_init

def format_entry(feedly_entry):
  body = f'''<b><a href="{feedly_entry['url']}">{feedly_entry['title']}</a></b>
source: <a href="{feedly_entry['sourceUrl']}">{feedly_entry['source']}</a>'''
  preview = f"preview: <i>{feedly_entry['preview']}</i>"

  if feedly_entry['preview']:
    return body + '\n' + preview

  return body

def format_digest(intro, feedly_entries):
  nl = '\n\n'

  return f'''{intro}\n
{nl.join([format_entry(entry) for entry in feedly_entries])}'''

feedly_api = FeedlyApi(feedly_access_token, feedly_refresh_token)
telegram_api = TelegramChannelBotApi(telegram_bot_token, telegram_channel)

# abort if failed to connect to the API
if not feedly_api.active:
  print('Failed to access the Feedly API.')
  exit()

def post_news():
  print('Executing the daily digest job...')

  # we use frequency as lifespan in order to only fetch articles from the past FREQ hours
  news_result = feedly_api.collect_content(news_feed_label, frequency, count = digest_count)
  sm_result = feedly_api.collect_content(sm_feed_label, frequency, count = digest_count)

  # abort if couldn't fetch news data from Feedly
  if not news_result['success']:
    print('Error fetching data from Feedly. Details:')
    print(news_result['error'])
    return

  # abort if couldn't fetch sm data from Feedly
  if not sm_result['success']:
    print('Error fetching data from Feedly. Details:')
    print(sm_result['error'])
    return

  # send news digest
  news = news_result['data']
  message = format_digest(INTRO_NEWS, news)
  print(message)
  result = telegram_api.send_message(message)

  # abort if couldn't send a message to the channel
  if not result['success']:
    print('Error sending a message to TG Channel. Details:')
    print(result['error'])
    return

  # send social media digest
  sm = sm_result['data']
  message = format_digest(INTRO_SM, sm)
  print(message)
  result = telegram_api.send_message(message)

  # abort if couldn't send a message to the channel
  if not result['success']:
    print('Error sending a message to TG Channel. Details:')
    print(result['error'])
    return

  print('Successfully sent a digest!')

schedule.every(frequency).hours.at(publish_time).do(post_news)

print('Starting the schedule poll with the following parameters:')
print(f'TG Channel: {telegram_channel}\n'\
      f'Feedly News Feed Label: {news_feed_label}\n'\
      f'Feedly Social Media Feed Label: {sm_feed_label}\n'\
      f'Digest Count: {digest_count}\n'\
      f'Publish time: {publish_time}\n'\
      f'Frequency: {frequency}\n'\
      f'Force Start: {force_init}')

# force a digest post upon initialization if flag set
if force_init:
  post_news()

while True:
  schedule.run_pending()
  time.sleep(60)
