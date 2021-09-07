import requests

class TelegramChannelBotApi:
  def __init__(self, bot_token, channel_name):
    self.token = bot_token
    self.channel = channel_name
    self.base_url = f'https://api.telegram.org/bot{bot_token}'

  def send_message(self, message):
    params = {
      'chat_id': self.channel,
      'text': message,
      'parse_mode': 'html',
      'disable_web_page_preview': True,
    }

    result = requests.get(f'{self.base_url}/sendMessage', params = params)

    if result.status_code != 200:
      return {
        'success': False,
        'error': result.json()
      }
    
    return {
      'success': True
    }