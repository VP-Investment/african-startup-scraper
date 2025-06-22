import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import schedule
import time
import logging
from datetime import datetime, timedelta
import json
import re
from typing import List, Dict, Optional
import os
from dataclasses import dataclass
import sqlite3
import threading
from flask import Flask, request, jsonify, render_template_string
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('startup_scraper.log'),
        logging.StreamHandler()
    ]
)

@dataclass
class StartupNews:
    title: str
    url: str
    description: str
    source: str
    date: str
    startup_name: str = ""
    category: str = ""

class AfricanStartupScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Initialize database
        self.init_database()
        
        # Expanded comprehensive launch signals regex pattern
        self.LAUNCH_SIGNALS = re.compile(
            r"""
            \b(
                # core launch verbs
                launch(?:es|ed|ing)? |
                ship(?:s|ped|ping)? |
                release(?:s|d|ing)? |
                roll(?:s|ed)?\s*out |
                debut(?:s|ed|ing)? |
                unveil(?:s|ed|ing)? |
                introduce(?:s|d|ing)? |
                # "go live" family
                go(?:es)?\s*live |
                we'?re\s+live |
                now\s*live |
                now\s+available |
                # beta / early-access
                public\s+beta |
                private\s+beta |
                early\s+access |
                soft\s+launch |
                MVP\s+live |
                v(?:\d+\.)?\d+\s*release |        # v1.0, v2.3.1, etc.
                # stealth exits
                out\s+of\s+stealth |
                emerges?\s+from\s+stealth |
                exits?\s+stealth\s*mode |
                breaks?\s+cover |
                # wait-list / sign-up
                waitlist\s+open |
                sign[-\s]*ups?\s+open |
                open\s*for\s*signups? |
                # funding-tied cues
                secures?\s+pre[-\s]*seed |
                raises?\s+angel\s+round |
                funded\s+to\s+launch |
                # accelerator / demo-day
                joins?\s+.*\baccelerator\b |
                graduates?\s+from\s+accelerator |
                demo\s*day\s*debut |
                # market / product expansion
                enters?\s+new\s+market |
                expands?\s+to |
                opens?\s+operations\s+in |
                adds?\s+new\s+platform |
                launches?\s+in |
                # additional signals
                new\s+product |
                new\s+service |
                new\s+platform |
                new\s+app |
                new\s+feature |
                announce(?:s|d|ing)? |
                reveal(?:s|ed|ing)? |
                present(?:s|ed|ing)? |
                showcase(?:s|d|ing)? |
                expansion |
                milestone |
                breakthrough |
                innovation |
                partnership |
                collaboration |
                integration |
                upgrade(?:s|d|ing)? |
                enhancement(?:s)? |
                improvement(?:s)? |
                beta\s+test |
                pilot\s+program |
                pre[-\s]*launch |
                coming\s+soon |
                available\s+now
            )\b
            """, 
            re.VERBOSE | re.IGNORECASE
        )
        
        # Comprehensive list of African startup news sources
        self.sources = {
            'techcabal': {
                'url': 'https://techcabal.com',
                'parser': self.parse_generic_wordpress
            },
            'techpoint_africa': {
                'url': 'https://techpoint.africa',
                'parser': self.parse_generic_wordpress
            },
            'benjamindada': {
                'url': 'https://www.benjamindada.com',
                'parser': self.parse_generic_wordpress
            },
            'disrupt_africa': {
                'url': 'https://disrupt-africa.com',
                'parser': self.parse_generic_wordpress
            },
            'technext': {
                'url': 'https://technext24.com',
                'parser': self.parse_generic_wordpress
            },
            'techtrendske': {
                'url': 'https://techtrendske.co.ke',
                'parser': self.parse_generic_wordpress
            },
            'digest_africa': {
                'url': 'https://digestafrica.com',
                'parser': self.parse_generic_wordpress
            },
            'tech_moran': {
                'url': 'https://techmoran.com',
                'parser': self.parse_generic_wordpress
            },
            'innovation_village': {
                'url': 'https://innovation-village.com',
                'parser': self.parse_generic_wordpress
            },
            'startup_nigeria': {
                'url': 'https://startupnigeria.org',
                'parser': self.parse_generic_wordpress
            },
            'the_flip_africa': {
                'url': 'https://theflip.africa',
                'parser': self.parse_generic_wordpress
            },
            'tech_safari': {
                'url': 'https://www.techsafari.africa',
                'parser': self.parse_generic_wordpress
            },
            'ventureburn': {
                'url': 'https://ventureburn.com',
                'parser': self.parse_generic_wordpress
            },
            'wamda': {
                'url': 'https://www.wamda.com',
                'parser': self.parse_generic_wordpress
            },
            'startupbrics': {
                'url': 'https://startupbrics.com',
                'parser': self.parse_generic_wordpress
            },
            'tech_in_africa': {
                'url': 'https://techinafrica.com',
                'parser': self.parse_generic_wordpress
            },
            'baobab_insights': {
                'url': 'https://baobabinsights.com',
                'parser': self.parse_generic_wordpress
            },
            'weetracker': {
                'url': 'https://weetracker.com',
                'parser': self.parse_generic_wordpress
            },
            'techbuild_africa': {
                'url': 'https://techbuild.africa',
                'parser': self.parse_generic_wordpress
            },
            'founders_africa': {
                'url': 'https://foundersafrica.com',
                'parser': self.parse_generic_wordpress
            },
            'techeconomy': {
                'url': 'https://techeconomy.ng',
                'parser': self.parse_generic_wordpress
            },
            'techgh24': {
                'url': 'https://techgh24.com',
                'parser': self.parse_generic_wordpress
            },
            'technova_ghana': {
                'url': 'https://technovagh.com',
                'parser': self.parse_generic_wordpress
            },
            'african_business': {
                'url': 'https://african.business',
                'parser': self.parse_generic_wordpress
            },
            'iafrikan': {
                'url': 'https://www.iafrikan.com',
                'parser': self.parse_generic_wordpress
            },
            'zikoko_tech': {
                'url': 'https://www.zikoko.com',
                'parser': self.parse_generic_wordpress
            }
        }

    def init_database(self):
        """Initialize SQLite database to track sent articles"""
        conn = sqlite3.connect('sent_articles.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sent_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                title TEXT,
                sent_date DATE,
                source TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def is_article_sent(self, url: str) -> bool:
        """Check if article was already sent"""
        conn = sqlite3.connect('sent_articles.db')
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM sent_articles WHERE url = ?', (url,))
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0

    def mark_article_sent(self, article: StartupNews):
        """Mark article as sent"""
        conn = sqlite3.connect('sent_articles.db')
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO sent_articles (url, title, sent_date, source)
                VALUES (?, ?, ?, ?)
            ''', (article.url, article.title, datetime.now().date(), article.source))
            conn.commit()
        except sqlite3.IntegrityError:
            pass  # Article already exists
        conn.close()

    def contains_launch_keywords(self, text: str) -> bool:
        """Check if text contains launch-related keywords using advanced regex"""
        return bool(self.LAUNCH_SIGNALS.search(text))

    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a webpage"""
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            logging.error(f"Error fetching {url}: {e}")
            return None

    def parse_generic_wordpress(self, soup: BeautifulSoup, source_name: str) -> List[StartupNews]:
        """Generic parser for WordPress-based sites"""
        articles = []
        try:
            # Try multiple common WordPress article selectors
            article_selectors = [
                'article',
                '.post',
                '.entry',
                '.content-item',
                '.post-item',
                '.article-item',
                '.blog-post',
                '[class*="post"]',
                '[class*="article"]'
            ]
            
            found_articles = []
            for selector in article_selectors:
                found_articles = soup.select(selector)[:15]
                if found_articles:
                    break
            
            for article in found_articles:
                # Try to find title
                title_elem = None
                title_selectors = ['h1', 'h2', 'h3', '.entry-title', '.post-title', '.article-title', '.title']
                for t_sel in title_selectors:
                    title_elem = article.select_one(t_sel)
                    if title_elem:
                        break
                
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                
                # Try to find URL
                url = None
                link_elem = title_elem.find('a') or article.find('a')
                if link_elem and link_elem.get('href'):
                    url = link_elem['href']
                    # Handle relative URLs
                    if url.startswith('/'):
                        from urllib.parse import urljoin, urlparse
                        base_url = f"{urlparse(self.sources[source_name]['url']).scheme}://{urlparse(self.sources[source_name]['url']).netloc}"
                        url = urljoin(base_url, url)
                
                if not url:
                    continue
                
                # Try to find description
                description = ""
                desc_selectors = ['.entry-content', '.post-content', '.excerpt', '.summary', '.description', 'p']
                for d_sel in desc_selectors:
                    desc_elem = article.select_one(d_sel)
                    if desc_elem:
                        description = desc_elem.get_text(strip=True)[:300] + "..."
                        break
                
                # Try to find date
                date = datetime.now().strftime('%Y-%m-%d')
                date_selectors = ['time', '.date', '.post-date', '.entry-date', '[datetime]']
                for date_sel in date_selectors:
                    date_elem = article.select_one(date_sel)
                    if date_elem:
                        date_text = date_elem.get('datetime') or date_elem.get_text(strip=True)
                        if date_text:
                            date = date_text
                        break
                
                # Check if it's about product/service launch
                full_text = title + " " + description
                if self.contains_launch_keywords(full_text):
                    articles.append(StartupNews(
                        title=title,
                        url=url,
                        description=description,
                        source=source_name.replace('_', ' ').title(),
                        date=date
                    ))
                    
        except Exception as e:
            logging.error(f"Error parsing {source_name}: {e}")
        
        return articles

    def scrape_all_sources(self) -> List[StartupNews]:
        """Scrape all configured news sources"""
        all_articles = []
        
        for source_name, source_config in self.sources.items():
            logging.info(f"Scraping {source_name}...")
            try:
                soup = self.fetch_page(source_config['url'])
                if soup:
                    articles = source_config['parser'](soup, source_name)
                    # Filter out already sent articles
                    new_articles = [article for article in articles if not self.is_article_sent(article.url)]
                    all_articles.extend(new_articles)
                    logging.info(f"Found {len(new_articles)} new articles from {source_name}")
                else:
                    logging.warning(f"Failed to fetch {source_name}")
                    
                # Add small delay between requests to be respectful
                time.sleep(1)
                
            except Exception as e:
                logging.error(f"Error scraping {source_name}: {e}")
        
        return all_articles

    def generate_email_content(self, articles: List[StartupNews]) -> str:
        """Generate HTML email content"""
        if not articles:
            return """
            <html>
            <body>
                <h2>🚀 African Startup Daily Digest</h2>
                <p><strong>Date:</strong> {}</p>
                <p>No new startup launches found today. Check back tomorrow!</p>
            </body>
            </html>
            """.format(datetime.now().strftime('%B %d, %Y'))
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background-color: #2c3e50; color: white; padding: 20px; text-align: center; }}
                .article {{ border: 1px solid #ddd; margin: 20px 0; padding: 15px; border-radius: 5px; }}
                .article h3 {{ color: #2c3e50; margin-top: 0; }}
                .source {{ background-color: #3498db; color: white; padding: 5px 10px; border-radius: 3px; font-size: 12px; }}
                .date {{ color: #7f8c8d; font-size: 14px; }}
                .description {{ margin: 10px 0; }}
                .read-more {{ background-color: #e74c3c; color: white; padding: 8px 15px; text-decoration: none; border-radius: 3px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🚀 African Startup Daily Digest</h1>
                <p><strong>Date:</strong> {datetime.now().strftime('%B %d, %Y')}</p>
                <p>Latest Product & Service Launches from African Startups</p>
            </div>
            
            <div style="padding: 20px;">
                <p><strong>Found {len(articles)} new startup launches today!</strong></p>
        """
        
        for article in articles:
            html_content += f"""
                <div class="article">
                    <h3>{article.title}</h3>
                    <p><span class="source">{article.source}</span> <span class="date">{article.date}</span></p>
                    <div class="description">{article.description}</div>
                    <a href="{article.url}" class="read-more" target="_blank">Read Full Story</a>
                </div>
            """
        
        html_content += """
            </div>
            
            <div style="background-color: #ecf0f1; padding: 20px; text-align: center; margin-top: 40px;">
                <p><em>This digest is automatically generated. Stay updated with the latest African startup ecosystem!</em></p>
            </div>
        </body>
        </html>
        """
        
        return html_content

    def send_email(self, articles: List[StartupNews], email_config: Dict):
        """Send email with scraped articles"""
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = email_config['sender_email']
            msg['To'] = ', '.join(email_config['recipients'])
            msg['Subject'] = f"🚀 African Startup Digest - {datetime.now().strftime('%B %d, %Y')} ({len(articles)} launches)"
            
            # Create HTML content
            html_content = self.generate_email_content(articles)
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port']) as server:
                server.starttls()
                server.login(email_config['sender_email'], email_config['sender_password'])
                server.send_message(msg)
            
            logging.info(f"Email sent successfully to {len(email_config['recipients'])} recipients")
            
            # Mark articles as sent
            for article in articles:
                self.mark_article_sent(article)
                
        except Exception as e:
            logging.error(f"Error sending email: {e}")

    def daily_scrape_and_send(self, email_config: Dict):
        """Main function to scrape and send daily digest"""
        logging.info("Starting daily scrape and send...")
        
        try:
            # Scrape all sources
            articles = self.scrape_all_sources()
            
            # Send email regardless of whether we found articles
            self.send_email(articles, email_config)
            
            logging.info(f"Daily digest completed. Found {len(articles)} new articles.")
            return len(articles)
            
        except Exception as e:
            logging.error(f"Error in daily scrape and send: {e}")
            return 0
    
    # Email configuration - UPDATE THESE VALUES
    EMAIL_CONFIG = {
    	'sender_email': os.getenv('SENDER_EMAIL', 'vpinvestment@venturesplatform.com'),
    	'sender_password': os.getenv('SENDER_PASSWORD', 'napsgqyupxuuitvo'),
   	'recipients': os.getenv('RECIPIENTS', 'vpinvestment@venturesplatform.com', 'sola@venturesplatform.com').split(','),
    	'smtp_server': 'smtp.gmail.com',
   	 'smtp_port': 587
    }
    
    # Initialize scraper
    global scraper_instance, email_config_global
    scraper_instance = AfricanStartupScraper()
    email_config_global = EMAIL_CONFIG

# Add debug logging
print(f"=== INITIALIZATION COMPLETE ===")
print(f"scraper_instance: {scraper_instance}")
print(f"email_config_global: {email_config_global}")
print(f"=== END INITIALIZATION ===")

# Flask web interface for manual triggers and cloud deployment
app = Flask(__name__)

@app.route('/')
def dashboard():
    """Simple web dashboard"""
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>African Startup Scraper Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .button { background-color: #3498db; color: white; padding: 15px 30px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; margin: 10px; text-decoration: none; display: inline-block; }
            .button:hover { background-color: #2980b9; }
            .button.danger { background-color: #e74c3c; }
            .button.danger:hover { background-color: #c0392b; }
            .status { padding: 20px; background-color: #ecf0f1; border-radius: 5px; margin: 20px 0; }
            h1 { color: #2c3e50; text-align: center; }
            .info { background-color: #d5e8f5; padding: 15px; border-radius: 5px; margin: 10px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 African Startup Scraper Dashboard</h1>
            
            <div class="info">
                <h3>Control Panel</h3>
                <p>This dashboard allows you to manually trigger scraping and manage the automated system.</p>
            </div>
            
            <div class="status">
                <h3>Quick Actions</h3>
                <a href="/trigger" class="button">🔄 Trigger Manual Scrape & Send</a>
                <a href="/status" class="button">📊 Check Status</a>
                <a href="/logs" class="button">📝 View Recent Logs</a>
            </div>
            
            <div class="info">
                <h3>Scheduled Operation</h3>
                <p>✅ Automatic daily digest at 9:00 AM</p>
                <p>📧 Email notifications enabled</p>
                <p>🔍 Monitoring {{ sources_count }} African startup news sources</p>
            </div>
        </div>
    </body>
    </html>
    """, sources_count=len(scraper_instance.sources) if scraper_instance else 0)

@app.route('/trigger')
def trigger_scrape():
    """Manually trigger scraping"""
    print("=== TRIGGER ENDPOINT CALLED ===")  # Debug log
    
    # Safely check if variables exist
    try:
        scraper_exists = scraper_instance is not None
        print(f"scraper_instance exists: {scraper_exists}")
    except NameError:
        print("ERROR: scraper_instance is not defined at all!")
        scraper_exists = False
        
    try:
        email_exists = email_config_global is not None
        print(f"email_config_global exists: {email_exists}")
    except NameError:
        print("ERROR: email_config_global is not defined at all!")
        email_exists = False
    
    if scraper_exists and email_exists:
        try:
            print("Starting manual scrape...")  # Debug log
            print(f"Scraper instance: {type(scraper_instance)}")  # Debug log
            print(f"Email config: {email_config_global is not None}")  # Debug log
            
            # Call the scraping function with better error context
            articles_count = scraper_instance.daily_scrape_and_send(email_config_global)
            
            print(f"Scrape completed successfully. Articles found: {articles_count}")  # Debug log
            
            return jsonify({
                'status': 'success',
                'message': f'Manual scrape completed. Found {articles_count} new articles.',
                'articles_count': articles_count,
                'timestamp': datetime.now().isoformat()
            })
            
        except AttributeError as e:
            error_msg = f"Scraper method error: {str(e)}"
            print(f"ERROR - AttributeError: {error_msg}")
            return jsonify({
                'status': 'error',
                'message': error_msg,
                'error_type': 'AttributeError',
                'timestamp': datetime.now().isoformat()
            }), 500
            
        except Exception as e:
            error_msg = f"Scraping failed: {str(e)}"
            print(f"ERROR - General Exception: {error_msg}")
            print(f"Exception type: {type(e)}")
            return jsonify({
                'status': 'error',
                'message': error_msg,
                'error_type': str(type(e).__name__),
                'timestamp': datetime.now().isoformat()
            }), 500
    
    # Handle missing components
    missing_items = []
    if not scraper_exists:
        missing_items.append("scraper_instance")
    if not email_exists:
        missing_items.append("email_config_global")
        
    error_msg = f"Missing required components: {', '.join(missing_items)}"
    print(f"ERROR - Missing components: {error_msg}")
    
    return jsonify({
        'status': 'error',
        'message': error_msg,
        'missing_components': missing_items,
        'timestamp': datetime.now().isoformat()
    }), 500

@app.route('/status')
def get_status():
    """Get current system status"""
    return jsonify({
        'status': 'running',
        'sources_count': len(scraper_instance.sources) if scraper_instance else 0,
        'next_scheduled_run': '09:00 daily',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/logs')
def get_logs():
    """Get recent logs"""
    try:
        with open('startup_scraper.log', 'r') as f:
            logs = f.readlines()[-50:]  # Last 50 lines
        return '<pre>' + ''.join(logs) + '</pre>'
    except:
        return 'No logs available'

def run_scheduler():
    """Run the scheduler in a separate thread"""
    while True:
        schedule.run_pending()
        time.sleep(60)

def main():
    """Main function with cloud deployment support"""
    global scraper_instance, email_config_global
    
    parser = argparse.ArgumentParser(description='African Startup News Scraper')
    parser.add_argument('--mode', choices=['local', 'cloud'], default='local',
                       help='Run mode: local (with scheduler) or cloud (web service)')
    parser.add_argument('--port', type=int, default=5000,
                       help='Port for web service (cloud mode)')
    
    args = parser.parse_args()
    
    if args.mode == 'cloud':
        # Cloud mode - run as web service (for deployment on Heroku, Railway, etc.)
        logging.info("Starting in CLOUD mode - web service")
        
        # Schedule daily execution
        schedule.every().day.at("09:00").do(
            scraper_instance.daily_scrape_and_send, 
            email_config=EMAIL_CONFIG
        )
        
        # Start scheduler in background thread
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        
        # Run Flask app
        app.run(host='0.0.0.0', port=args.port, debug=False)
        
    else:
        # Local mode - traditional scheduler
        logging.info("Starting in LOCAL mode - traditional scheduler")
        
        # Schedule daily execution at 9:00 AM
        schedule.every().day.at("09:00").do(
            scraper_instance.daily_scrape_and_send, 
            email_config=EMAIL_CONFIG
        )
        
        logging.info("African Startup Scraper started. Scheduled to run daily at 9:00 AM")
        logging.info("Press Ctrl+C to stop the scheduler")
        
        # Run once immediately for testing
        print("Running initial scrape...")
        scraper_instance.daily_scrape_and_send(EMAIL_CONFIG)
        
        # Keep the script running
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logging.info("Scheduler stopped by user")

if __name__ == "__main__":
    import sys
    import os
    
    # Check if running in cloud mode
    if '--mode' in sys.argv and 'cloud' in sys.argv:
        port = int(os.environ.get("PORT", 5000))
        # Initialize scraper in cloud mode
        scraper = AfricanStartupScraper()
        app.run(host="0.0.0.0", port=port)
    else:
        # Local mode
        main()
