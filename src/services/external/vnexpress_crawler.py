import requests
from bs4 import BeautifulSoup
import re

class VnExpressCrawler:
    def __init__(self):
        self.base_url = "https://vnexpress.net"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def search_travel_articles(self, keyword):
        try:
            # Search for articles
            search_url = f"{self.base_url}/search?q={keyword}"
            response = requests.get(search_url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract article links
            articles = []
            for article in soup.find_all('article', class_='item-news'):
                title_elem = article.find('h2', class_='title-news')
                if title_elem and 'du-lich' in title_elem.find('a')['href']:
                    articles.append({
                        'title': title_elem.text.strip(),
                        'url': title_elem.find('a')['href'],
                        'description': article.find('p', class_='description').text.strip() if article.find('p', class_='description') else ''
                    })
            
            return articles[:5]  # Return top 5 articles
        except Exception as e:
            print(f"Error crawling VnExpress: {str(e)}")
            return []
    
    def get_article_content(self, url):
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract article content
            content = soup.find('article', class_='fck_detail')
            if not content:
                return None
            
            # Extract text and images
            text = ' '.join([p.text.strip() for p in content.find_all('p')])
            images = [img['src'] for img in content.find_all('img') if img.get('src')]
            
            return {
                'text': text,
                'images': images
            }
        except Exception as e:
            print(f"Error getting article content: {str(e)}")
            return None 