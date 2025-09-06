import logging
import requests
import re
import time
import os
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.constants import ChatAction

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration - use environment variables for production
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_TELEGRAM_BOT_TOKEN')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', 'YOUR_GOOGLE_API_KEY')

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
            "/examples - See examples\n\n"
            "🔍 **Search Types:**\n"
            "📍 ZIP: `90210`\n"
            "🏛️ State: `CA`\n"
            "🏙️ City: `Miami FL`"
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
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
        
        # State Code: 2 letters
        elif re.match(r'^[A-Z]{2}$', user_input):
            return 'state', user_input
        
        # City + State: "CITY ST" format
        elif re.match(r'^[A-Z\s]+\s[A-Z]{2}$', user_input):
            parts = user_input.rsplit(' ', 1)
            city = parts[0].title()
            state = parts[1]
            return 'city_state', f"{city}, {state}"
        
        return 'unknown', user_input
    
    def geocode_location(self, search_query, search_type):
        """Convert search query to coordinates."""
        try:
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            
            if search_type == 'state':
                search_query = f"{search_query}, USA"
            elif search_type == 'city_state':
                search_query = f"{search_query}, USA"
            
            params = {
                'address': search_query,
                'key': GOOGLE_API_KEY,
                'components': 'country:US'
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if data['status'] == 'OK' and data['results']:
                result = data['results'][0]
                location = result['geometry']['location']
                formatted_address = result['formatted_address']
                
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
            
            return None, None, None, None, None
            
        except Exception as e:
            logger.error(f"Geocoding error: {e}")
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
            
            response = requests.get(url, params=params)
            data = response.json()
            
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
                    
                    time.sleep(0.1)  # Rate limiting
            
            return stations
            
        except Exception as e:
            logger.error(f"Gas station search error: {e}")
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
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if data['status'] == 'OK':
                return data['result']
            
            return {}
            
        except Exception as e:
            logger.error(f"Place details error: {e}")
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
        
        # Detect search type
        search_type, processed_input = self.detect_search_type(user_input)
        
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
                stations = self.cache[cache_key]['stations']
                area_info = self.cache[cache_key]['area_info']
                
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=status_msg.message_id
                )
                
                response_text = self.create_response(stations, area_info, search_type)
                await update.message.reply_text(response_text, parse_mode='Markdown')
                return
        
        # Geocode the search
        lat, lng, city, state, formatted_address = self.geocode_location(processed_input, search_type)
        
        if not lat or not lng:
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
            pass  # Ignore if message already deleted
        
        # Send results only once
        response_text = self.create_response(stations, area_info, search_type)
        await update.message.reply_text(response_text, parse_mode='Markdown')

def main():
    """Main function to run the bot."""
    print("🚀 Starting Simple Gas Station Finder Bot...")
    print("✅ Clean, organized interface")
    print("📱 Bot starting...")
    
    try:
        # Create bot instance
        bot = SimpleGasStationBot()
        
        # Create application
        app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Add handlers
        app.add_handler(CommandHandler("start", bot.start))
        app.add_handler(CommandHandler("help", bot.help_command))
        app.add_handler(CommandHandler("examples", bot.examples_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
        
        # Start the bot
        print("✅ Bot started successfully!")
        app.run_polling()
        
    except Exception as e:
        print(f"❌ Error starting bot: {e}")

if __name__ == '__main__':
    main()