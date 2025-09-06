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

class BeautifulGasStationBot:
    def __init__(self):
        self.cache = {}  # Cache results to save API costs
    
    async def start(self, update, context):
        """Send welcome message when /start command is issued."""
        welcome_text = (
            "⛽ **BEAUTIFUL GAS STATION FINDER** ⛽\n\n"
            "🎯 **Choose your search method:**\n\n"
            "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
            "┃  🗺️  **SEARCH OPTIONS**              ┃\n"
            "┃                                     ┃\n"
            "┃  📍 **ZIP Code**                    ┃\n"
            "┃  Example: `90210`                   ┃\n"
            "┃                                     ┃\n"
            "┃  🏛️  **State Code**                 ┃\n"
            "┃  Example: `CA` or `TX`              ┃\n"
            "┃                                     ┃\n"
            "┃  🏙️  **City + State**               ┃\n"
            "┃  Example: `Miami FL` or `Boston MA` ┃\n"
            "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
            "✨ **What you'll get:**\n"
            "🎯 **3 top gas stations** per search\n"
            "📍 **Complete addresses** & details\n"
            "⭐ **Ratings & reviews** included\n"
            "⚡ **Instant results** - no waiting!\n\n"
            "💡 **Ready to find gas stations?**\n"
            "Just send your search term!"
        )
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def help_command(self, update, context):
        """Send help message."""
        help_text = (
            "🆘 **HELP & COMMANDS** 🆘\n\n"
            "📋 **Available Commands:**\n"
            "/start - Welcome & search options\n"
            "/help - This help message\n"
            "/about - About this bot\n"
            "/examples - Search examples\n\n"
            "🔍 **Search Methods:**\n\n"
            "**1. ZIP Code Search:**\n"
            "• Send: `90210`\n"
            "• Gets: 3 stations in Beverly Hills, CA\n\n"
            "**2. State Search:**\n"
            "• Send: `CA` or `TX`\n"
            "• Gets: 3 popular stations in that state\n\n"
            "**3. City + State Search:**\n"
            "• Send: `Miami FL`\n"
            "• Gets: 3 stations in Miami, Florida\n\n"
            "🎯 **All searches return 3 top-rated stations!**"
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def about_command(self, update, context):
        """Send about message."""
        about_text = (
            "ℹ️ **ABOUT GAS STATION FINDER** ℹ️\n\n"
            "🤖 **What I do:**\n"
            "Find the **3 best gas stations** in your area using real-time data from Google Places API\n\n"
            "🎨 **Features:**\n"
            "🎯 Beautiful, clean interface\n"
            "📍 Multiple search options\n"
            "⭐ Real ratings & reviews\n"
            "⚡ Lightning-fast results\n"
            "🔄 Smart caching system\n\n"
            "🔧 **Technology:**\n"
            "• Google Places API\n"
            "• Python & Docker\n"
            "• Hosted on Render\n\n"
            "📊 **Data Quality:**\n"
            "All information is real-time and verified from Google's database of businesses."
        )
        await update.message.reply_text(about_text, parse_mode='Markdown')
    
    async def examples_command(self, update, context):
        """Send example searches."""
        examples_text = (
            "📝 **SEARCH EXAMPLES** 📝\n\n"
            "🎯 **ZIP Code Examples:**\n"
            "`90210` - Beverly Hills, CA\n"
            "`10001` - New York, NY\n"
            "`77001` - Houston, TX\n"
            "`60601` - Chicago, IL\n\n"
            "🏛️ **State Code Examples:**\n"
            "`CA` - California stations\n"
            "`TX` - Texas stations\n"
            "`FL` - Florida stations\n"
            "`NY` - New York stations\n\n"
            "🏙️ **City + State Examples:**\n"
            "`Miami FL` - Miami, Florida\n"
            "`Boston MA` - Boston, Massachusetts\n"
            "`Seattle WA` - Seattle, Washington\n"
            "`Denver CO` - Denver, Colorado\n\n"
            "💡 **Tips:**\n"
            "• State codes are 2 letters (CA, TX, FL)\n"
            "• For cities, use: `CityName StateName`\n"
            "• All searches return 3 top stations\n\n"
            "🚀 **Try any example above!**"
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
                # For state search, get the state capital or major city
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
    
    def search_gas_stations(self, lat, lng, area_info):
        """Search for top 3 gas stations near coordinates."""
        try:
            url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            
            # Adjust radius based on search type
            radius = 15000  # 15km for broader search
            
            params = {
                'location': f"{lat},{lng}",
                'radius': radius,
                'type': 'gas_station',
                'key': GOOGLE_API_KEY
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            stations = []
            if data['status'] == 'OK':
                # Sort by rating first, then by user_ratings_total
                places = sorted(data['results'], 
                              key=lambda x: (x.get('rating', 0), x.get('user_ratings_total', 0)), 
                              reverse=True)
                
                for place in places[:3]:  # Top 3 stations
                    details = self.get_place_details(place['place_id'])
                    
                    station = {
                        'name': place.get('name', 'Unknown Station'),
                        'address': details.get('formatted_address', place.get('vicinity', 'Address not available')),
                        'rating': place.get('rating', 0),
                        'user_ratings_total': place.get('user_ratings_total', 0),
                        'price_level': place.get('price_level', None),
                        'opening_hours': self.format_opening_hours(details.get('opening_hours', {})),
                        'phone': details.get('formatted_phone_number', ''),
                        'website': details.get('website', ''),
                        'place_id': place['place_id']
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
                'fields': 'formatted_address,formatted_phone_number,website,opening_hours',
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
    
    def format_opening_hours(self, hours_data):
        """Format opening hours."""
        try:
            if 'weekday_text' in hours_data:
                return hours_data['weekday_text'][0]  # Today's hours
            return "Hours not available"
        except:
            return "Hours not available"
    
    def create_beautiful_response(self, stations, search_info, search_type):
        """Create a beautiful response with the 3 gas stations."""
        if not stations:
            return (
                "❌ **NO STATIONS FOUND** ❌\n\n"
                f"🔍 **Searched:** {search_info}\n"
                f"📍 **Search Type:** {search_type.title()}\n\n"
                "💡 **Try a different search:**\n"
                "• Different ZIP code\n"
                "• Different city/state\n"
                "• Broader area search"
            )
        
        response = f"🎉 **TOP {len(stations)} GAS STATIONS** 🎉\n\n"
        response += f"📍 **Location:** {search_info}\n"
        response += f"🔍 **Search Type:** {search_type.replace('_', ' ').title()}\n\n"
        response += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for i, station in enumerate(stations, 1):
            # Station header with number and name
            response += f"**{i}. 🏪 {station['name']}**\n"
            
            # Address
            response += f"📍 {station['address']}\n"
            
            # Rating and reviews
            if station['rating'] > 0:
                stars = "⭐" * int(station['rating'])
                response += f"{stars} **{station['rating']}/5** ({station['user_ratings_total']} reviews)\n"
            
            # Hours
            if station['opening_hours'] != "Hours not available":
                response += f"🕒 {station['opening_hours']}\n"
            
            # Phone
            if station['phone']:
                response += f"📞 {station['phone']}\n"
            
            # Price indicator
            if station['price_level'] is not None:
                price_symbols = "$" * (station['price_level'] + 1)
                response += f"💰 Price Level: {price_symbols}\n"
            
            response += "\n"
            
            # Add separator between stations (but not after the last one)
            if i < len(stations):
                response += "┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n\n"
        
        response += "🔄 **Want more stations? Try a different search!**"
        return response
    
    async def handle_message(self, update, context):
        """Handle user search input."""
        user_input = update.message.text.strip()
        
        # Detect search type
        search_type, processed_input = self.detect_search_type(user_input)
        
        if search_type == 'unknown':
            await update.message.reply_text(
                "❓ **SEARCH FORMAT NOT RECOGNIZED** ❓\n\n"
                "🎯 **Please use one of these formats:**\n\n"
                "📍 **ZIP Code:** `90210`\n"
                "🏛️ **State:** `CA` or `TX`\n"
                "🏙️ **City + State:** `Miami FL`\n\n"
                "💡 **Examples:**\n"
                "• `90210` (Beverly Hills ZIP)\n"
                "• `CA` (California state)\n"
                "• `Boston MA` (Boston, Massachusetts)\n\n"
                "Send /examples to see more options!",
                parse_mode='Markdown'
            )
            return
        
        # Show processing message
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        
        status_msg = await update.message.reply_text(
            f"🔍 **SEARCHING FOR GAS STATIONS...**\n\n"
            f"📍 **Search:** {processed_input}\n"
            f"🎯 **Type:** {search_type.replace('_', ' ').title()}\n"
            f"⚡ **Finding top 3 stations...**"
        )
        
        # Check cache
        cache_key = f"{search_type}_{processed_input.lower()}"
        if cache_key in self.cache:
            cached_time = self.cache[cache_key]['timestamp']
            if time.time() - cached_time < 1800:  # 30 minutes
                stations = self.cache[cache_key]['stations']
                area_info = self.cache[cache_key]['area_info']
                
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=status_msg.message_id,
                    text=f"📋 **USING CACHED RESULTS**\n\n"
                         f"⚡ **Found {len(stations)} stations instantly!**"
                )
                
                response_text = self.create_beautiful_response(stations, area_info, search_type)
                await update.message.reply_text(response_text, parse_mode='Markdown')
                return
        
        # Geocode the search
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=status_msg.message_id,
            text=f"🗺️ **LOCATING AREA...**\n\n"
                 f"📍 **Search:** {processed_input}\n"
                 f"🎯 **Getting coordinates...**"
        )
        
        lat, lng, city, state, formatted_address = self.geocode_location(processed_input, search_type)
        
        if not lat or not lng:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=status_msg.message_id,
                text=f"❌ **LOCATION NOT FOUND**\n\n"
                     f"🔍 **Searched for:** {processed_input}\n"
                     f"💡 **Please try:**\n"
                     f"• Different spelling\n"
                     f"• Valid ZIP code\n"
                     f"• Correct state abbreviation"
            )
            return
        
        # Search for gas stations
        area_info = f"{city}, {state}" if city != "Unknown" else formatted_address
        
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=status_msg.message_id,
            text=f"⛽ **FINDING GAS STATIONS...**\n\n"
                 f"📍 **Area:** {area_info}\n"
                 f"🎯 **Getting top 3 stations...**"
        )
        
        stations = self.search_gas_stations(lat, lng, area_info)
        
        # Cache results
        self.cache[cache_key] = {
            'stations': stations,
            'area_info': area_info,
            'timestamp': time.time()
        }
        
        # Delete status message
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=status_msg.message_id
        )
        
        # Send beautiful results
        response_text = self.create_beautiful_response(stations, area_info, search_type)
        await update.message.reply_text(response_text, parse_mode='Markdown')

def main():
    """Main function to run the bot."""
    print("🚀 Starting Beautiful Gas Station Finder Bot...")
    print("🎨 Features:")
    print("   • Beautiful interface design")
    print("   • 3 search methods: ZIP, State, City+State")
    print("   • Top 3 gas stations per search")
    print("   • Real-time Google Places data")
    print("   • Smart caching system")
    print("📱 Bot starting...")
    
    try:
        # Create bot instance
        bot = BeautifulGasStationBot()
        
        # Create application
        app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Add handlers
        app.add_handler(CommandHandler("start", bot.start))
        app.add_handler(CommandHandler("help", bot.help_command))
        app.add_handler(CommandHandler("about", bot.about_command))
        app.add_handler(CommandHandler("examples", bot.examples_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
        
        # Start the bot
        print("✅ Bot started successfully!")
        print("💡 Send /start to your bot to begin")
        app.run_polling()
        
    except Exception as e:
        print(f"❌ Error starting bot: {e}")

if __name__ == '__main__':
    main()