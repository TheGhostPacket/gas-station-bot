import logging
import requests
import csv
import io
import re
import time
import os
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import ChatAction

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration - use environment variables for production
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_TELEGRAM_BOT_TOKEN')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', 'YOUR_GOOGLE_API_KEY')

class GooglePlacesGasStationBot:
    def __init__(self):
        self.cache = {}  # Cache results to save API costs
    
    def start(self, update, context):
        """Send welcome message when /start command is issued."""
        welcome_text = (
            "⛽🔥 **GAS STATION FINDER** 🔥⛽\n\n"
            "🚗💨 Find real gas stations instantly!\n\n"
            "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
            "┃  📍 **HOW TO USE**                      ┃\n"
            "┃  🎯 Send any US ZIP code               ┃\n"
            "┃  📊 Get 5 gas stations instantly       ┃\n"
            "┃  💾 Download as CSV file               ┃\n"
            "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
            "🌟 **EXAMPLES:**\n"
            "• `90210` - Beverly Hills, CA\n"
            "• `10001` - New York, NY  \n"
            "• `77001` - Houston, TX\n"
            "• `60601` - Chicago, IL\n\n"
            "✨ **FEATURES:**\n"
            "🔥 Real-time Google Places data\n"
            "🎯 Smart address parsing\n"
            "💾 Instant CSV download\n"
            "⚡ Lightning fast results\n"
            "🚀 Up to 10 ZIP codes supported\n\n"
            "💡 **TIP:** Send multiple ZIP codes separated by spaces!\n"
            "Example: `90210 10001 77001`\n\n"
            "🎯 **Ready to find gas stations? Send a ZIP code!**"
        )
        update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    def extract_zip_codes(self, text):
        """Extract valid US ZIP codes from text."""
        # Find all 5-digit numbers in the text
        zip_codes = re.findall(r'\b\d{5}\b', text.strip())
        
        # Remove duplicates while preserving order
        unique_zips = []
        for zip_code in zip_codes:
            if zip_code not in unique_zips:
                unique_zips.append(zip_code)
        
        # Limit to 10 ZIP codes maximum
        return unique_zips[:10]
    
    def geocode_zip_code(self, zip_code):
        """Convert ZIP code to coordinates using Google Geocoding API."""
        try:
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                'address': zip_code,
                'key': GOOGLE_API_KEY,
                'components': 'country:US'  # Limit to US
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if data['status'] == 'OK' and data['results']:
                result = data['results'][0]
                location = result['geometry']['location']
                formatted_address = result['formatted_address']
                
                # Extract city and state from formatted address
                address_parts = formatted_address.split(', ')
                city = address_parts[1] if len(address_parts) > 1 else "Unknown"
                state = address_parts[2].split()[0] if len(address_parts) > 2 else "Unknown"
                
                return location['lat'], location['lng'], city, state, formatted_address
            
            return None, None, None, None, None
            
        except Exception as e:
            logger.error(f"Geocoding error: {e}")
            return None, None, None, None, None
    
    def search_gas_stations(self, lat, lng, zip_code):
        """Search for gas stations near the given coordinates."""
        try:
            url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            params = {
                'location': f"{lat},{lng}",
                'radius': 8000,  # 8km radius
                'type': 'gas_station',
                'key': GOOGLE_API_KEY
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            stations = []
            if data['status'] == 'OK':
                for place in data['results']:
                    # Get detailed info for each place
                    details = self.get_place_details(place['place_id'])
                    
                    # Extract address components
                    address_info = self.parse_address(details.get('formatted_address', ''), zip_code)
                    
                    station = {
                        'name': place.get('name', 'Unknown Station'),
                        'address': address_info['street_address'],
                        'city': address_info['city'],
                        'state': address_info['state'],
                        'zip': address_info['zip'],
                        'full_address': details.get('formatted_address', place.get('vicinity', ''))
                    }
                    stations.append(station)
                    
                    # Small delay to be respectful to API
                    time.sleep(0.1)
            
            return stations[:5]  # Return max 5 stations per ZIP
            
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
    
    def parse_address(self, full_address, target_zip):
        """Parse full address into components."""
        try:
            if not full_address:
                return {
                    'street_address': 'Address not available',
                    'city': 'Unknown',
                    'state': 'Unknown',
                    'zip': target_zip
                }
            
            # Split address by commas
            parts = [part.strip() for part in full_address.split(',')]
            
            if len(parts) >= 3:
                street_address = parts[0]
                city = parts[1]
                
                # Last part usually contains state and ZIP
                last_part = parts[-1].strip()
                
                # Extract state (2 letters) and ZIP (5 digits)
                state_zip_match = re.search(r'([A-Z]{2})\s+(\d{5})', last_part)
                if state_zip_match:
                    state = state_zip_match.group(1)
                    zip_code = state_zip_match.group(2)
                else:
                    # Fallback
                    state_parts = last_part.split()
                    state = state_parts[0] if state_parts else 'Unknown'
                    zip_code = target_zip
                
                return {
                    'street_address': street_address,
                    'city': city,
                    'state': state,
                    'zip': zip_code
                }
            
            # Fallback for malformed addresses
            return {
                'street_address': full_address.split(',')[0] if ',' in full_address else full_address,
                'city': 'Unknown',
                'state': 'Unknown',
                'zip': target_zip
            }
            
        except Exception as e:
            logger.error(f"Address parsing error: {e}")
            return {
                'street_address': 'Address parsing error',
                'city': 'Unknown',
                'state': 'Unknown',
                'zip': target_zip
            }
    
    def create_horizontal_csv_content(self, all_stations_data):
        """Create horizontal CSV content with Seller Name1, Address1, etc. format."""
        try:
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Create header row with horizontal format
            header = []
            max_stations = max(len(stations) for stations in all_stations_data.values()) if all_stations_data else 0
            
            for i in range(1, max_stations + 1):
                header.extend([
                    f'Seller Name{i}',
                    f'Seller Address{i}',
                    f'Seller City{i}',
                    f'Seller State{i}',
                    f'Seller Zip{i}'
                ])
            
            writer.writerow(header)
            
            # Create data row
            data_row = []
            station_index = 0
            
            # Flatten all stations from all ZIP codes
            all_stations = []
            for zip_code in sorted(all_stations_data.keys()):
                all_stations.extend(all_stations_data[zip_code])
            
            # Fill the horizontal row
            for i in range(max_stations):
                if i < len(all_stations):
                    station = all_stations[i]
                    data_row.extend([
                        station['name'],
                        station['address'],
                        station['city'],
                        station['state'],
                        station['zip']
                    ])
                else:
                    # Fill empty columns if we have fewer stations
                    data_row.extend(['', '', '', '', ''])
            
            writer.writerow(data_row)
            
            csv_content = output.getvalue()
            output.close()
            
            return csv_content
            
        except Exception as e:
            logger.error(f"CSV creation error: {e}")
            return None
    
    def create_csv_file(self, csv_content, zip_codes):
        """Create a CSV file object for sending."""
        try:
            csv_bytes = io.BytesIO()
            csv_bytes.write(csv_content.encode('utf-8'))
            csv_bytes.seek(0)
            
            if len(zip_codes) == 1:
                csv_bytes.name = f"gas_stations_{zip_codes[0]}.csv"
            else:
                csv_bytes.name = f"gas_stations_{'_'.join(zip_codes[:3])}.csv"
            
            return csv_bytes
            
        except Exception as e:
            logger.error(f"Error creating CSV file: {e}")
            return None
    
    def create_nice_preview(self, all_stations_data, zip_codes):
        """Create a nice preview of the gas stations."""
        try:
            preview_text = "🎉 **GAS STATIONS FOUND!** 🎉\n\n"
            
            total_stations = sum(len(stations) for stations in all_stations_data.values())
            
            preview_text += f"📊 **SUMMARY:**\n"
            preview_text += f"🎯 ZIP Codes: {len(zip_codes)}\n"
            preview_text += f"⛽ Total Stations: {total_stations}\n"
            preview_text += f"💾 CSV Format: Horizontal layout\n\n"
            
            preview_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            station_counter = 1
            for zip_code in sorted(all_stations_data.keys()):
                stations = all_stations_data[zip_code]
                if stations:
                    preview_text += f"📍 **ZIP {zip_code}** - {stations[0]['city']}, {stations[0]['state']}\n"
                    
                    for station in stations:
                        preview_text += f"  {station_counter}. 🏪 **{station['name']}**\n"
                        preview_text += f"     📌 {station['address']}\n"
                        preview_text += f"     🏙️ {station['city']}, {station['state']} {station['zip']}\n\n"
                        station_counter += 1
                    
                    preview_text += "┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n\n"
            
            preview_text += "💾 **Download the CSV file above for horizontal format!**\n"
            preview_text += "🔄 Send more ZIP codes to search again!"
            
            return preview_text
            
        except Exception as e:
            logger.error(f"Preview creation error: {e}")
            return "Preview generation error"
    
    def handle_message(self, update, context):
        """Handle user ZIP code input."""
        user_input = update.message.text.strip()
        
        # Extract ZIP codes from input
        zip_codes = self.extract_zip_codes(user_input)
        
        if not zip_codes:
            update.message.reply_text(
                "❌ **NO VALID ZIP CODES FOUND!** \n\n"
                "🎯 **Examples:**\n"
                "• `90210`\n"
                "• `90210 10001 77001`\n"
                "• `Multiple: 60601 33101 94102`\n\n"
                "📝 **Tips:**\n"
                "• Use 5-digit US ZIP codes\n"
                "• Separate multiple ZIPs with spaces\n"
                "• Maximum 10 ZIP codes per request",
                parse_mode='Markdown'
            )
            return
        
        # Show processing message
        context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        
        if len(zip_codes) == 1:
            status_message = update.message.reply_text(
                f"🔍 **SEARCHING ZIP {zip_codes[0]}...**\n\n"
                f"⚡ Finding gas stations..."
            )
        else:
            status_message = update.message.reply_text(
                f"🔍 **SEARCHING {len(zip_codes)} ZIP CODES...**\n\n"
                f"📍 ZIPs: {', '.join(zip_codes)}\n"
                f"⚡ Finding gas stations..."
            )
        
        all_stations_data = {}
        processed_count = 0
        
        for zip_code in zip_codes:
            processed_count += 1
            
            # Update status
            context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=status_message.message_id,
                text=f"🔍 **PROCESSING... ({processed_count}/{len(zip_codes)})**\n\n"
                     f"📍 Current: ZIP {zip_code}\n"
                     f"⚡ Generating gas station data..."
            )
            
            # Check cache first
            cache_key = zip_code
            if cache_key in self.cache:
                cached_time = self.cache[cache_key]['timestamp']
                if time.time() - cached_time < 1800:  # Cache for 30 minutes
                    all_stations_data[zip_code] = self.cache[cache_key]['stations']
                    continue
            
            # Geocode ZIP code
            lat, lng, city, state, formatted_address = self.geocode_zip_code(zip_code)
            
            if not lat or not lng:
                logger.warning(f"Could not geocode ZIP {zip_code}")
                all_stations_data[zip_code] = []
                continue
            
            # Search for gas stations
            stations = self.search_gas_stations(lat, lng, zip_code)
            all_stations_data[zip_code] = stations
            
            # Cache the result
            self.cache[cache_key] = {
                'stations': stations,
                'timestamp': time.time()
            }
            
            # Small delay between requests
            time.sleep(0.5)
        
        # Check if we found any stations
        total_stations = sum(len(stations) for stations in all_stations_data.values())
        
        if total_stations == 0:
            context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=status_message.message_id,
                text=f"❌ **NO GAS STATIONS FOUND!**\n\n"
                     f"📍 Searched: {', '.join(zip_codes)}\n"
                     f"💡 Try different ZIP codes"
            )
            return
        
        # Update status to generating CSV
        context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=status_message.message_id,
            text=f"📊 **GENERATING CSV FILE...**\n\n"
                 f"⛽ Found {total_stations} gas stations\n"
                 f"💾 Creating horizontal CSV format..."
        )
        
        # Create CSV content
        csv_content = self.create_horizontal_csv_content(all_stations_data)
        
        if not csv_content:
            context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=status_message.message_id,
                text="❌ **CSV GENERATION FAILED!**\n\nPlease try again."
            )
            return
        
        # Create CSV file
        csv_file = self.create_csv_file(csv_content, zip_codes)
        
        if not csv_file:
            context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=status_message.message_id,
                text="❌ **FILE CREATION FAILED!**\n\nPlease try again."
            )
            return
        
        # Send CSV file
        try:
            zip_list = ', '.join(zip_codes[:5])
            if len(zip_codes) > 5:
                zip_list += f" (+{len(zip_codes)-5} more)"
            
            context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=csv_file,
                filename=csv_file.name,
                caption=f"⛽🔥 **GAS STATIONS CSV** 🔥⛽\n\n"
                       f"📍 **ZIP Codes:** {zip_list}\n"
                       f"📊 **Total Stations:** {total_stations}\n"
                       f"💾 **Format:** Horizontal CSV\n"
                       f"🎯 **Layout:** Seller Name1, Address1, City1, State1, Zip1, etc.\n\n"
                       f"🚀 **Ready for your next search!**",
                parse_mode='Markdown'
            )
            
            # Delete status message
            context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=status_message.message_id
            )
            
            # Send nice preview
            preview_text = self.create_nice_preview(all_stations_data, zip_codes)
            update.message.reply_text(preview_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error sending file: {e}")
            context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=status_message.message_id,
                text="❌ **FILE SENDING FAILED!**\n\nPlease try again."
            )

def main():
    """Main function to run the bot."""
    print("🚀 Starting Google Places Gas Station Finder Bot...")
    print("🌟 Features:")
    print("   • Real gas station data from Google Places API")
    print("   • Multiple ZIP codes support (up to 10)")
    print("   • Horizontal CSV format")
    print("   • Beautiful UI with emojis")
    print("   • 30-minute caching to save API costs")
    print("💰 API Cost: ~$0.10-0.50 per ZIP code")
    print("📱 Bot starting...")
    
    try:
        # Create bot instance
        bot = GooglePlacesGasStationBot()
        
        # Create updater and dispatcher
        updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
        dispatcher = updater.dispatcher
        
        # Add handlers
        dispatcher.add_handler(CommandHandler("start", bot.start))
        dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, bot.handle_message))
        
        # Start the bot
        updater.start_polling()
        print("✅ Bot started successfully!")
        print("💡 Send /start to your bot to begin")
        updater.idle()
        
    except Exception as e:
        print(f"❌ Error starting bot: {e}")

if __name__ == '__main__':
    main()