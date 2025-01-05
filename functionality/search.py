import threading
from bs4 import BeautifulSoup
from utils.gemini import *
from utils.redis_utils import *
import requests
from tenacity import retry, stop_after_attempt

@retry(stop=stop_after_attempt(2))
def get_organic_results_serper_dev(query, num_results=3, location="Malaysia"):
    query = query.strip().replace('*', '').replace('"', '')
    if cached := get_generic_cache('get_organic_results_serper_dev:' + query):
        return cached
        
    headers = {
        'X-API-KEY': os.getenv('SERPER_DEV_API_KEY'),
        'Content-Type': 'application/json'
    }
    data = json.dumps({
        "q": query,
        "location": location,
        "num": num_results,
        "page": 1
    })
    
    response = requests.post('https://google.serper.dev/search', headers=headers, data=data)
    response.raise_for_status()
    result = response.json()
    
    organic = result.get('organic', [])
    urls = [result['link'] for result in organic]
    if urls:
        set_generic_cache('get_organic_results_serper_dev:' + query, urls, 60 * 60 * 12)
    return urls

@retry(stop=stop_after_attempt(2))
def scrape_website_crawlbase(url: str):
    try:
        response = requests.get(f'https://api.crawlbase.com/?token={os.getenv("CRAWLBASE_API_KEY")}&url=' + url)
    except Exception as e:
        return ''
        
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        paragraphs = soup.find_all('p')
        scraped_data = [p.get_text() for p in paragraphs]
        formatted_data = "\n".join(scraped_data)
        set_generic_cache('scrape_website:' + url, formatted_data)
        return formatted_data
    return ''

def scrape_url_with_timeout(news_data, url):
    try:
        result = scrape_website_crawlbase(url)
        if result:
            news_data.append(result)
    except Exception:
        pass

def scrape_urls_threaded(news_data: list, news_urls: list):
    threads = []
    for url in news_urls:
        thread = threading.Thread(target=scrape_url_with_timeout, args=(news_data, url))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join(timeout=45)

def google_search_pipeline(message: str):
    google_search_query = generate_google_search_query(message)
    if not google_search_query:
        return "Could not generate search query"
        
    try:
        news_urls = get_organic_results_serper_dev(google_search_query)
        if not news_urls:
            return "No results found for this query"
            
        news_data = []
        scrape_urls_threaded(news_data, news_urls)
        if not news_data:
            return "Could not retrieve content from search results"
            
        response = retrieve_scraped_data_short_answer('\n\n'.join(news_data), message)
        return response if response else "No relevant information found"
        
    except Exception as e:
        return f"Search failed: {str(e)}"