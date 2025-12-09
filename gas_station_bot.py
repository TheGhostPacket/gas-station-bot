import logging
import requests
import re
import time
import os
import threading
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.constants import ChatAction
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration - use environment variables for production
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_TELEGRAM_BOT_TOKEN')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', 'YOUR_GOOGLE_API_KEY')

# Debug: Log if API key is set
if GOOGLE_API_KEY == 'YOUR_GOOGLE_API_KEY':
    logger.warning("⚠️ GOOGLE_API_KEY not set! Using placeholder.")
else:
    logger.info(f"✅ GOOGLE_API_KEY loaded (starts with: {GOOGLE_API_KEY[:10]}...)")

# US State codes to full names for better geocoding
US_STATES = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
    'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
    'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
    'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
    'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
    'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
    'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
    'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
    'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
    'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
    'WI': 'Wisconsin', 'WY': 'Wyoming', 'DC': 'Washington DC'
}

# State capitals for better results when searching by state
STATE_CAPITALS = {
    'AL': 'Montgomery, AL', 'AK': 'Anchorage, AK', 'AZ': 'Phoenix, AZ', 'AR': 'Little Rock, AR',
    'CA': 'Los Angeles, CA', 'CO': 'Denver, CO', 'CT': 'Hartford, CT', 'DE': 'Wilmington, DE',
    'FL': 'Miami, FL', 'GA': 'Atlanta, GA', 'HI': 'Honolulu, HI', 'ID': 'Boise, ID',
    'IL': 'Chicago, IL', 'IN': 'Indianapolis, IN', 'IA': 'Des Moines, IA', 'KS': 'Kansas City, KS',
    'KY': 'Louisville, KY', 'LA': 'New Orleans, LA', 'ME': 'Portland, ME', 'MD': 'Baltimore, MD',
    'MA': 'Boston, MA', 'MI': 'Detroit, MI', 'MN': 'Minneapolis, MN', 'MS': 'Jackson, MS',
    'MO': 'St. Louis, MO', 'MT': 'Billings, MT', 'NE': 'Omaha, NE', 'NV': 'Las Vegas, NV',
    'NH': 'Manchester, NH', 'NJ': 'Newark, NJ', 'NM': 'Albuquerque, NM', 'NY': 'New York, NY',
    'NC': 'Charlotte, NC', 'ND': 'Fargo, ND', 'OH': 'Columbus, OH', 'OK': 'Oklahoma City, OK',
    'OR': 'Portland, OR', 'PA': 'Philadelphia, PA', 'RI': 'Providence, RI', 'SC': 'Charleston, SC',
    'SD': 'Sioux Falls, SD', 'TN': 'Nashville, TN', 'TX': 'Houston, TX', 'UT': 'Salt Lake City, UT',
    'VT': 'Burlington, VT', 'VA': 'Virginia Beach, VA', 'WA': 'Seattle, WA', 'WV': 'Charleston, WV',
    'WI': 'Milwaukee, WI', 'WY': 'Cheyenne, WY', 'DC': 'Washington, DC'
}

class HealthHandler(SimpleHTTPRequestHandler):
    """Simple HTTP handler for health checks."""
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Gas Station Bot is running!')
    
    def log_message(self, format, *args):
        pass  # Suppress HTTP logs

def start_health_server():
    """Start a simple HTTP server for Render health checks."""
    port = int(os.getenv('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    print(f"🌐 Health server started on port {port}")
    server.serve_forever()

class SimpleGasStationBot:
    def __init__(self):
        self.cache = {}  # Cache results to save API costs
    
    async def start(self, update, context):
        """Send welcome message when /start command is issued."""
        welcome_text = (
            "⛽ **GAS STATION FINDER**\n\n"
            "🔍 **Search Methods:**\n"
            "📍 ZIP Code: `90210`\n"
            "🏛️ State: `CA` or `TX`\n"
            "🏙️ City + State: `Miami FL`\n\n"
            "✅ Returns 3 top gas stations\n"
            "📍 Just send your search term!"
        )
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def help_command(self, update, context):
        """Send help message."""
        help_text = (
            "🆘 **HELP**\n\n"
            "📋 **Commands:**\n"
            "/start - Welcome message\n"
            "/help - This help\n"
            "/examples - See examples\n"
            "/commands - All commands\n\n"
            "🔍 **Search Types:**\n"
            "📍 ZIP: `90210`\n"
            "🏛️ State: `CA`\n"
            "🏙️ City: `Miami FL`"
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def commands_command(self, update, context):
        """List all available commands."""
        commands_text = (
            "📋 **COMMANDS**\n\n"
            "/start - Start the bot\n"
            "/help - Get help\n"
            "/examples - See search examples\n"
            "/commands - This list"
        )
        await update.message.reply_text(commands_text, parse_mode='Markdown')
    
    async def examples_command(self, update, context):
        """Send example searches."""
        examples_text = (
            "📝 **EXAMPLES**\n\n"
            "📍 **ZIP Codes:**\n"
            "`90210` - Beverly Hills, CA\n"
            "`10001` - New York, NY\n"
            "`77001` - Houston, TX\n\n"
            "🏛️ **States:**\n"
            "`CA` - California\n"
            "`TX` - Texas\n"
            "`FL` - Florida\n\n"
            "🏙️ **City + State:**\n"
            "`Miami FL`\n"
            "`Boston MA`\n"
            "`Seattle WA`"
        )
        await update.message.reply_text(examples_text, parse_mode='Markdown')
    
    def detect_search_type(self, user_input):
        """Detect what type of search the user wants."""
        user_input = user_input.strip().upper()
        
        # ZIP Code: 5 digits
        if re.match(r'^\d{5}$', user_input):
            return 'zip', user_input
        
        # State Code: 2 letters (must be valid US state)
        elif re.match(r'^[A-Z]{2}$', user_input):
            if user_input in US_STATES:
                return 'state', user_input
            else:
                return 'unknown', user_input
        
        # City + State: "CITY ST" format
        elif re.match(r'^[A-Z\s]+\s[A-Z]{2}$', user_input):
            parts = user_input.rsplit(' ', 1)
            city = parts[0].title()
            state = parts[1]
            if state in US_STATES:
                return 'city_state', f"{city}, {state}"
            else:
                return 'unknown', user_input
        
        return 'unknown', user_input
    
    def geocode_location(self, search_query, search_type):
        """Convert search query to coordinates."""
        try:
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            
            # For state searches, use the major city instead of state center
            if search_type == 'state' and search_query in STATE_CAPITALS:
                search_query = STATE_CAPITALS[search_query]
                logger.info(f"🔄 State search converted to: {search_query}")
            elif search_type == 'state':
                search_query = f"{US_STATES.get(search_query, search_query)}, USA"
            elif search_type == 'city_state':
                search_query = f"{search_query}, USA"
            elif search_type == 'zip':
                search_query = f"{search_query}, USA"
            
            params = {
                'address': search_query,
                'key': GOOGLE_API_KEY,
                'components': 'country:US'
            }
            
            logger.info(f"🔍 Geocoding request: {search_query}")
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            logger.info(f"📍 Geocoding status: {data.get('status')}")
            
            if data['status'] == 'OK' and data['results']:
                result = data['results'][0]
                location = result['geometry']['location']
                formatted_address = result['formatted_address']
                
                logger.info(f"✅ Found location: {formatted_address} ({location['lat']}, {location['lng']})")
                
                # Extract location info
                state = "Unknown"
                city = "Unknown"
                
                if 'address_components' in result:
                    for component in result['address_components']:
                        types = component.get('types', [])
                        if 'administrative_area_level_1' in types:
                            state = component.get('short_name', 'Unknown')
                        elif 'locality' in types:
                            city = component.get('long_name', 'Unknown')
                
                return location['lat'], location['lng'], city, state, formatted_address
            else:
                logger.error(f"❌ Geocoding failed: {data.get('status')} - {data.get('error_message', 'No error message')}")
            
            return None, None, None, None, None
            
        except Exception as e:
            logger.error(f"❌ Geocoding exception: {e}")
            return None, None, None, None, None
    
    def search_gas_stations(self, lat, lng):
        """Search for top 3 gas stations near coordinates."""
        try:
            url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            
            params = {
                'location': f"{lat},{lng}",
                'radius': 15000,  # 15km radius
                'type': 'gas_station',
                'key': GOOGLE_API_KEY
            }
            
            logger.info(f"🔍 Searching gas stations at: {lat}, {lng}")
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            logger.info(f"⛽ Places API status: {data.get('status')}, Results: {len(data.get('results', []))}")
            
            stations = []
            if data['status'] == 'OK':
                # Sort by rating first
                places = sorted(data['results'], 
                              key=lambda x: (x.get('rating', 0), x.get('user_ratings_total', 0)), 
                              reverse=True)
                
                for place in places[:3]:  # Top 3 stations
                    details = self.get_place_details(place['place_id'])
                    
                    station = {
                        'name': place.get('name', 'Unknown Station'),
                        'address': details.get('formatted_address', place.get('vicinity', 'Address not available'))
                    }
                    stations.append(station)
                    logger.info(f"✅ Found station: {station['name']}")
                    
                    time.sleep(0.1)  # Rate limiting
            else:
                logger.error(f"❌ Places API error: {data.get('status')} - {data.get('error_message', '')}")
            
            return stations
            
        except Exception as e:
            logger.error(f"❌ Gas station search exception: {e}")
            return []
    
    def get_place_details(self, place_id):
        """Get detailed place information."""
        try:
            url = "https://maps.googleapis.com/maps/api/place/details/json"
            params = {
                'place_id': place_id,
                'fields': 'formatted_address',
                'key': GOOGLE_API_KEY
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data['status'] == 'OK':
                return data['result']
            
            return {}
            
        except Exception as e:
            logger.error(f"❌ Place details exception: {e}")
            return {}
    
    def create_response(self, stations, search_info, search_type):
        """Create clean response like the VIN format."""
        if not stations:
            return (
                f"❌ **NO STATIONS FOUND**\n\n"
                f"🔍 **Search:** {search_info}\n"
                f"💡 Try a different location"
            )
        
        response = f"⛽ **GAS STATIONS FOUND**\n\n"
        response += f"📍 **Location:** {search_info}\n"
        response += f"🔍 **Search Type:** {search_type.replace('_', ' ').title()}\n\n"
        response += f"📋 **Station Details:**\n"
        
        for i, station in enumerate(stations, 1):
            response += f"🏪 **Station {i}:** {station['name']}\n"
            response += f"📍 **Address:** {station['address']}\n"
            
            # Add separator between stations (but not after the last one)
            if i < len(stations):
                response += "\n"
        
        return response
    
    async def handle_message(self, update, context):
        """Handle user search input."""
        user_input = update.message.text.strip()
        
        logger.info(f"📩 Received message: {user_input}")
        
        # Detect search type
        search_type, processed_input = self.detect_search_type(user_input)
        
        logger.info(f"🔎 Detected: type={search_type}, input={processed_input}")
        
        if search_type == 'unknown':
            await update.message.reply_text(
                "❓ **INVALID FORMAT**\n\n"
                "🔍 **Valid formats:**\n"
                "📍 ZIP: `90210`\n"
                "🏛️ State: `CA`\n"
                "🏙️ City: `Miami FL`\n\n"
                "Send /examples for more options",
                parse_mode='Markdown'
            )
            return
        
        # Show processing message
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        
        status_msg = await update.message.reply_text(
            f"🔍 **SEARCHING...**\n\n"
            f"📍 **Query:** {processed_input}\n"
            f"⚡ Finding gas stations..."
        )
        
        # Check cache
        cache_key = f"{search_type}_{processed_input.lower()}"
        if cache_key in self.cache:
            cached_time = self.cache[cache_key]['timestamp']
            if time.time() - cached_time < 1800:  # 30 minutes
                logger.info(f"📦 Using cached results for: {cache_key}")
                stations = self.cache[cache_key]['stations']
                area_info = self.cache[cache_key]['area_info']
                
                try:
                    await context.bot.delete_message(
                        chat_id=update.effective_chat.id,
                        message_id=status_msg.message_id
                    )
                except:
                    pass
                
                response_text = self.create_response(stations, area_info, search_type)
                await update.message.reply_text(response_text, parse_mode='Markdown')
                return
        
        # Geocode the search
        lat, lng, city, state, formatted_address = self.geocode_location(processed_input, search_type)
        
        if not lat or not lng:
            logger.error(f"❌ Geocoding failed for: {processed_input}")
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=status_msg.message_id,
                text=f"❌ **LOCATION NOT FOUND**\n\n"
                     f"🔍 **Searched:** {processed_input}\n"
                     f"💡 Please try a different search"
            )
            return
        
        # Search for gas stations
        area_info = f"{city}, {state}" if city != "Unknown" else formatted_address
        stations = self.search_gas_stations(lat, lng)
        
        # Cache results
        self.cache[cache_key] = {
            'stations': stations,
            'area_info': area_info,
            'timestamp': time.time()
        }
        
        # Delete status message and send results
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=status_msg.message_id
            )
        except:
            pass
        
        # Send results
        response_text = self.create_response(stations, area_info, search_type)
        await update.message.reply_text(response_text, parse_mode='Markdown')

def main():
    """Main function to run the bot."""
    print("🚀 Starting Simple Gas Station Finder Bot...")
    print("✅ Clean, organized interface")
    print("📱 Bot starting...")
    
    # Debug API key status
    if GOOGLE_API_KEY == 'YOUR_GOOGLE_API_KEY':
        print("⚠️ WARNING: GOOGLE_API_KEY environment variable not set!")
    else:
        print(f"✅ Google API Key loaded (starts with: {GOOGLE_API_KEY[:15]}...)")
    
    if TELEGRAM_BOT_TOKEN == 'YOUR_TELEGRAM_BOT_TOKEN':
        print("⚠️ WARNING: TELEGRAM_BOT_TOKEN environment variable not set!")
    else:
        print(f"✅ Telegram Bot Token loaded")
    
    try:
        # Start health server in background thread for Render
        health_thread = threading.Thread(target=start_health_server, daemon=True)
        health_thread.start()
        
        # Create bot instance
        bot = SimpleGasStationBot()
        
        # Create application
        app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Add handlers
        app.add_handler(CommandHandler("start", bot.start))
        app.add_handler(CommandHandler("help", bot.help_command))
        app.add_handler(CommandHandler("examples", bot.examples_command))
        app.add_handler(CommandHandler("commands", bot.commands_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
        
        # Start the bot
        print("✅ Bot started successfully!")
        app.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
