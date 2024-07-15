import logging
from logging.handlers import RotatingFileHandler
import os
import sys
from aiogram import Bot, Dispatcher, executor, types
import aiohttp
import aiogram
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime, date, timedelta
import time
import json
from collections import defaultdict
import asyncio
from urllib.parse import quote

# Configurations
API_TOKEN = '7333349269:AAF4-qtS8-S4C6xwI7gYVFfEmBB-qObheHU'
TON_API_KEY = 'AEPUWOTKOWQ6N4AAAAANXAT5ZOSYTZNK67Z2FLJBRQUQUVQRYG3EFWE2GAPNRNJVOE3TZBQ'

# Créer un dossier 'logs' s'il n'existe pas
if not os.path.exists('logs'):
    os.makedirs('logs')

# Configuration du logging
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Handler pour le fichier
file_handler = RotatingFileHandler('logs/bot.log', maxBytes=5*1024*1024, backupCount=5)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.DEBUG)

# Handler pour la console
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.INFO)

# Configurer le logger root
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

def force_flush_print(*args, **kwargs):
    print(*args, **kwargs)
    sys.stdout.flush()

async def async_log(message):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, logging.info, message)

def direct_log(message):
    with open('direct_log.txt', 'a') as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{timestamp} - {message}\n")

logging.info("Logging initialized")
force_flush_print("Logging handlers:", logging.getLogger().handlers)

# Initialisation du bot et du dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
logging.info("Bot started")

message_ids = {}

def format_large_number(number):
    if number is None:
        return "N/A"
    try:
        number = float(number)
    except ValueError:
        return str(number)
    
    if number >= 1_000_000_000:
        return f"{number / 1_000_000_000:.2f}B"
    elif number >= 1_000_000:
        return f"{number / 1_000_000:.2f}M"
    elif number >= 1_000:
        return f"{number / 1_000:.2f}K"
    else:
        return f"{number:.2f}"

async def fetch(session, url, headers):
    try:
        async with session.get(url, headers=headers) as response:
            response_text = await response.text()
            response_json = await response.json()
            return response_json
    except Exception as e:
        logging.error(f"Error in fetch: {e}")
        with open('response_dump.txt', 'w', encoding='utf-8') as file:
            file.write(response_text)
        raise ValueError(f"Failed to parse JSON response, content saved to 'response_dump.txt'. Error: {response_text}")

async def get_token_info(token_address):
    headers = {'Authorization': f'Bearer {TON_API_KEY}'}
    url = f"https://tonapi.io/v2/jettons/{token_address}"
    logging.info(f"Fetching token info from URL: {url}")
    try:
        async with aiohttp.ClientSession() as session:
            response = await fetch(session, url, headers)
            logging.info("Token info fetched successfully")
            return response
    except Exception as e:
        logging.error(f"Failed to get token info: {e}")
        return None

async def get_token_info_extended(token_address):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    headers = {'Content-Type': 'application/json'}
    logging.info(f"Fetching extended token info from URL: {url}")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('pairs') and len(data['pairs']) > 0:
                        pair = data['pairs'][0]
                        logging.info("Extended token info fetched successfully")
                        return {
                            'price': pair.get('priceUsd'),
                            'price_native': pair.get('priceNative'),
                            'market_cap': pair.get('fdv'),
                            'liquidity': pair.get('liquidity', {}).get('usd'),
                            'volume_24h': pair.get('volume', {}).get('h24'),
                            'price_change_24h': pair.get('priceChange', {}).get('h24'),
                            'txns_24h': {
                                'buys': pair.get('txns', {}).get('h24', {}).get('buys'),
                                'sells': pair.get('txns', {}).get('h24', {}).get('sells')
                            },
                            'pair_created_at': pair.get('pairCreatedAt'),
                            'dex_id': pair.get('dexId'),
                            'chain_id': pair.get('chainId'),
                            'pair_address': pair.get('pairAddress'),
                            'base_token': {
                                'address': pair.get('baseToken', {}).get('address'),
                                'name': pair.get('baseToken', {}).get('name'),
                                'symbol': pair.get('baseToken', {}).get('symbol')
                            },
                            'quote_token': {
                                'address': pair.get('quoteToken', {}).get('address'),
                                'name': pair.get('quoteToken', {}).get('name'),
                                'symbol': pair.get('quoteToken', {}).get('symbol')
                            },
                            'url': pair.get('url'),
                            'image_url': pair.get('info', {}).get('imageUrl'),
                            'websites': pair.get('info', {}).get('websites'),
                            'socials': pair.get('info', {}).get('socials')
                        }
                    else:
                        logging.error("No pairs found in the response")
                        return None
                else:
                    logging.error(f"Failed to retrieve token info: {response.status}")
                    return None
    except Exception as e:
        logging.error(f"Error in get_token_info_extended: {e}")
        return None

def get_square_number_emoji(number):
    square_numbers = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    return square_numbers[number - 1] if 1 <= number <= 10 else str(number)

@dp.message_handler(commands=['scan'])
async def scan_token(message: types.Message):
    try:
        logging.info("Scan command received")
        force_flush_print("Scan command received")
        direct_log(f"Scan command received in chat type: {message.chat.type}")
        logging.getLogger().handlers[0].flush()

        parts = message.text.split()
        if len(parts) < 2:
            await message.reply("Please provide a token address after the /scan command.")
            return
        token_address = parts[1]
        
        logging.info(f"Fetching token info for address: {token_address}")
        token_info = await get_token_info(token_address)
        logging.info("Token info fetched")
        extended_info = await get_token_info_extended(token_address)
        
        if not token_info or not extended_info:
            await message.reply("Failed to fetch token information.")
            return
        
        response_message = (
            f"📌 *Token:* [{token_info['metadata'].get('name', 'Non disponible')}](https://tonviewer.com/{token_address})\n\n"
            f"💲 *Current Price:* `${extended_info['price']}`\n"
            f"💰 *Market Cap:* ${format_large_number(extended_info['market_cap'])}\n"
            f"💦 *Liquidity:* ${format_large_number(extended_info['liquidity'])}\n"
            f"📊 *24h Volume:* ${format_large_number(extended_info['volume_24h'])}\n"
            f"📈 *24h Change:* {extended_info['price_change_24h']}%\n"
            f"🔄 *24h Transactions:* {extended_info['txns_24h']['buys']} buys, {extended_info['txns_24h']['sells']} sells\n\n"
            f"⚖️ *Pair:* {extended_info['base_token']['symbol']}/{extended_info['quote_token']['symbol']}\n"
            f"📅 *Pair Created:* {datetime.fromtimestamp(extended_info['pair_created_at']/1000).strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"🏦 *DEX:* {extended_info['dex_id']}\n"
            f"🔗 *Chain:* {extended_info['chain_id']}\n\n"
            f"⚠️ *Mintable:* `{token_info.get('mintable', 'Non disponible')}`\n"
            f"📦 *Total Supply:* `{token_info.get('total_supply', 'Non disponible')}`\n"
            f"👤 *Admin Address:* [{token_info['admin'].get('address', 'Non disponible')}](https://tonviewer.com/{token_info['admin'].get('address', 'Non disponible')})\n"
            f"📛 *Admin Name:* `{token_info['admin'].get('name', 'Non disponible')}`\n"
            f"🚨 *Is Scam:* `{token_info['admin'].get('is_scam', 'Non disponible')}`\n\n"
            f"🌐 *Social Links:* " + " | ".join([f"[{site['type']}]({site['url']})" for site in extended_info['socials']]) + "\n"
            f"🔗 *Websites:* " + " | ".join([f"[{site['label']}]({site['url']})" for site in extended_info['websites']]) + "\n"
            f"✔️ *Verification:* `{token_info.get('verification', 'Non disponible')}`\n"
            f"👥 *Holders Count:* `{token_info.get('holders_count', 'Non disponible')}`"
        )

        keyboard = InlineKeyboardMarkup()
        if message.chat.type in ['group', 'supergroup']:
            keyboard.add(InlineKeyboardButton("En savoir plus", url=f"https://t.me/{bot.username}?start=scan_{token_address}"))
        else:
            keyboard.add(InlineKeyboardButton("Chart", url=extended_info['url']),
                         InlineKeyboardButton("Holders", callback_data=f"holders|{token_address}"))
            keyboard.add(InlineKeyboardButton("Refresh", callback_data=f"refresh|{token_address}"))

        sent_message = await message.reply(response_message, parse_mode='Markdown', reply_markup=keyboard, disable_web_page_preview=True)
        
        if message.chat.type not in ['group', 'supergroup']:
            message_ids[token_address] = sent_message.message_id
        
        logging.info(f"Scan command completed for token: {token_address}")
    except Exception as e:
        logging.error(f"Error in scan_token: {e}")
        await message.reply("An error occurred while processing your request.")

@dp.callback_query_handler(lambda c: c.data.startswith('refresh|'))
async def handle_refresh(callback_query: types.CallbackQuery):
    try:
        token_address = callback_query.data.split('|')[1]
        logging.info(f"Refresh requested for token: {token_address}")
       
        token_info = await get_token_info(token_address)
        extended_info = await get_token_info_extended(token_address)
       
        if not token_info or not extended_info:
            await callback_query.answer("Failed to fetch token info.", show_alert=True)
            return

        admin_info = token_info.get('admin', {})
        metadata = token_info.get('metadata', {})

        response_message = (
            f"📌 *Token:* [{metadata.get('name', 'Non disponible')}](https://tonviewer.com/{token_address})\n\n"
            f"💲 *Current Price:* `${extended_info['price']}`\n"
            f"💰 *Market Cap:* ${format_large_number(extended_info['market_cap'])}\n"
            f"💦 *Liquidity:* ${format_large_number(extended_info['liquidity'])}\n"
            f"📊 *24h Volume:* ${format_large_number(extended_info['volume_24h'])}\n"
            f"📈 *24h Change:* {extended_info['price_change_24h']}%\n"
            f"🔄 *24h Transactions:* {extended_info['txns_24h']['buys']} buys, {extended_info['txns_24h']['sells']} sells\n\n"
            f"⚖️ *Pair:* {extended_info['base_token']['symbol']}/{extended_info['quote_token']['symbol']}\n"
            f"📅 *Pair Created:* {datetime.fromtimestamp(extended_info['pair_created_at']/1000).strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"🏦 *DEX:* {extended_info['dex_id']}\n"
            f"🔗 *Chain:* {extended_info['chain_id']}\n\n"
            f"⚠️ *Mintable:* `{token_info.get('mintable', 'Non disponible')}`\n"
            f"📦 *Total Supply:* `{token_info.get('total_supply', 'Non disponible')}`\n"
            f"👤 *Admin Address:* [{admin_info.get('address', 'Non disponible')}](https://tonviewer.com/{admin_info.get('address', 'Non disponible')})\n"
            f"📛 *Admin Name:* `{admin_info.get('name', 'Non disponible')}`\n"
            f"🚨 *Is Scam:* `{admin_info.get('is_scam', 'Non disponible')}`\n"
            f"🔖 *Metadata Address:* [{metadata.get('address', 'Non disponible')}](https://tonviewer.com/{metadata.get('address', 'Non disponible')})\n"
            f"🏷️ *Token Name:* `{metadata.get('name', 'Non disponible')}`\n"
            f"📐 *Symbol:* `{metadata.get('symbol', 'Non disponible')}`\n"
            f"🔢 *Decimals:* `{metadata.get('decimals', 'Non disponible')}`\n"
            f"📝 *Description:* `{metadata.get('description', 'Non disponible')}`\n\n"
            f"🌐 *Social Links:* " + 
            " | ".join([f"[{site['type']}]({site['url']})" for site in extended_info['socials']]) + "\n"
            f"🔗 *Websites:* " + 
            " | ".join([f"[{site['label']}]({site['url']})" for site in extended_info['websites']]) + "\n"
            f"✔️ *Verification:* `{token_info.get('verification', 'Non disponible')}`\n"
            f"👥 *Holders Count:* `{token_info.get('holders_count', 'Non disponible')}`"
        )

        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("Chart", url=extended_info['url']),
                     InlineKeyboardButton("Holders", callback_data=f"holders|{token_address}"))
        keyboard.add(InlineKeyboardButton("Refresh", callback_data=f"refresh|{token_address}"))

        try:
            await callback_query.message.edit_text(response_message, parse_mode='Markdown', reply_markup=keyboard, disable_web_page_preview=True)
        except aiogram.utils.exceptions.MessageNotModified:
            logging.info("Message not modified, content is the same")

        await callback_query.answer()
        logging.info(f"Refresh completed for token: {token_address}")
    except Exception as e:
        logging.error(f"Error in handle_refresh: {e}")
        await callback_query.answer("An error occurred while refreshing the data.", show_alert=True)

async def fetch_token_holders(token_address, limit=10):
    try:
        headers = {'Authorization': f'Bearer {TON_API_KEY}'}
        logging.info(f"Fetching token holders for address: {token_address}")
        url = f"https://tonapi.io/v2/jettons/{token_address}/holders?limit={limit}"
        async with aiohttp.ClientSession() as session:
            response = await session.get(url, headers=headers)
            if response.status == 200:
                data = await response.json()
                logging.info(f"Successfully fetched {len(data.get('addresses', []))} holders")
                return data.get('addresses', [])
            else:
                logging.error(f"Failed to fetch data: {response.status} {await response.text()}")
                return None
    except Exception as e:
        logging.error(f"Error in fetch_token_holders: {e}")
        return None
@dp.callback_query_handler(lambda c: c.data.startswith('holders|'))
async def handle_holders(callback_query: types.CallbackQuery):
    try:
        token_address = callback_query.data.split('|')[1]
        logging.info(f"Fetching holders for token: {token_address}")
        
        token_info = await get_token_info(token_address)
        extended_info = await get_token_info_extended(token_address)
       
        if not token_info or not extended_info:
            logging.error(f"Failed to fetch token info for {token_address}")
            await callback_query.answer("Failed to fetch token info.", show_alert=True)
            return

        current_price = float(extended_info['price']) if extended_info['price'] else 0
        total_supply = int(token_info.get('total_supply', '1'))
        token_symbol = token_info.get('metadata', {}).get('symbol', '')
        holders = await fetch_token_holders(token_address, limit=10)  # Fetch top 10 holders

        if not holders:
            logging.error(f"Failed to fetch holders for {token_address}")
            await callback_query.answer("Failed to fetch token holders or no holders found.", show_alert=True)
            return

        logging.info(f"Successfully fetched {len(holders)} holders for {token_address}")

        response_message = f"👥 *Top Token Holders for {token_symbol}:*\n\n"
        response_message += f"💲 *Current Price:* `${current_price}`\n"
        response_message += f"📊 *Market Cap:* `${format_large_number(extended_info['market_cap'])}`\n"
        response_message += f"💦 *Liquidity:* `${format_large_number(extended_info['liquidity'])}`\n"
        response_message += f"📈 *24h Change:* `{format_large_number(extended_info['volume_24h'])}%`\n\n"

        keyboard = InlineKeyboardMarkup()
        buttons = []

        for i, holder in enumerate(holders[:10], 1):
            balance = int(holder['balance'])
            balance_percent = (balance / total_supply) * 100 if total_supply else 0
            wallet_value_usd = balance * current_price
            address = holder['owner']['address']
            short_address = f"{address[:6]}...{address[-6:]}"
           
            square_number = get_square_number_emoji(i)
           
            response_message += (
                f"{square_number} `{short_address}`\n├─💰*{format_large_number(balance)} {token_symbol}*\n"
                f"├─💵 *~${format_large_number(wallet_value_usd)}*\n└─📊 `{balance_percent:.2f}%` of total supply\n\n"
            )
            buttons.append(InlineKeyboardButton(f"🔎 SCAN {i}", callback_data=f"scan_holder|{token_address}|{i}"))

        # Ajouter les boutons en deux colonnes
        for i in range(0, len(buttons), 2):
            if i + 1 < len(buttons):
                keyboard.row(buttons[i], buttons[i+1])
            else:
                keyboard.row(buttons[i])

        keyboard.row(InlineKeyboardButton("Chart", url=extended_info['url']),
                     InlineKeyboardButton("Refresh", callback_data=f"holders|{token_address}"))
        keyboard.add(InlineKeyboardButton("Back to Token Info", callback_data=f"refresh|{token_address}"))

        try:
            await callback_query.message.edit_text(response_message, parse_mode='Markdown', reply_markup=keyboard, disable_web_page_preview=True)
        except aiogram.utils.exceptions.MessageNotModified:
            logging.info("Message not modified, content is the same")
        except aiogram.utils.exceptions.MessageToEditNotFound:
            logging.warning("Message to edit not found, sending a new message")
            await callback_query.message.answer(response_message, parse_mode='Markdown', reply_markup=keyboard, disable_web_page_preview=True)

        await callback_query.answer()
        logging.info(f"Holders info displayed for {token_address}")
    except Exception as e:
        logging.error(f"Error in handle_holders: {e}")
        await callback_query.answer("An error occurred while fetching holders information.", show_alert=True)

async def analyze_transactions(token_address, limit=1000):
    try:
        logging.info(f"Analyzing transactions for token: {token_address}")
        # Fetch token info
        token_info = await get_token_info(token_address)
        if not token_info:
            logging.error(f"Failed to fetch token information for {token_address}")
            return "Failed to fetch token information."

        total_supply = int(token_info.get('total_supply', '1'))
        token_symbol = token_info.get('metadata', {}).get('symbol', 'TOKEN')

        # Fetch top holders
        holders = await fetch_token_holders(token_address, limit=10)
        if not holders:
            logging.error(f"Failed to fetch holders information for {token_address}")
            return "Failed to fetch holders information."

        suspicious_activities = []

        for holder in holders:
            holder_address = holder['owner']['address']
            holder_balance = int(holder['balance'])
            holder_percentage = (holder_balance / total_supply) * 100

            logging.info(f"Analyzing transactions for holder: {holder_address}")
            transactions = await get_recent_transactions(holder_address, limit)
            if not transactions:
                logging.info(f"No transactions found for holder: {holder_address}")
                continue

            out_transactions = []
            large_transactions = []
            token_transfers = []

            for tx in transactions:
                tx_type = "IN" if tx.get('in_msg', {}).get('source') else "OUT"
                if tx_type == "OUT":
                    for out_msg in tx.get('out_msgs', []):
                        amount = float(out_msg.get('value', 0)) / 1e9
                        tx_hash = tx.get('transaction_id', {}).get('hash', 'Unknown')
                        destination = out_msg.get('destination', 'Unknown')

                        out_transactions.append((amount, tx_hash, destination))

                        if amount > total_supply * 0.01:  # Transactions larger than 1% of total supply
                            large_transactions.append((amount, tx_hash, destination))

                        # Check for token transfers
                        if out_msg.get('message', '').startswith('te6'):  # This might indicate a token transfer
                            token_transfers.append((tx_hash, destination))

            if out_transactions or large_transactions or token_transfers:
                activity = f"Address: {holder_address[:6]}...{holder_address[-6:]}\n"
                activity += f"Balance: {holder_balance} {token_symbol} ({holder_percentage:.2f}% of supply)\n\n"

                if out_transactions:
                    activity += f"OUT transactions ({len(out_transactions)}):\n"
                    for amount, tx_hash, destination in out_transactions[:5]:  # Show top 5
                        activity += f"  • {amount:.2f} TON to {destination[:6]}...{destination[-6:]}\n"
                        activity += f"    TX: {tx_hash}\n"

                if large_transactions:
                    activity += f"\nLarge transactions ({len(large_transactions)}):\n"
                    for amount, tx_hash, destination in large_transactions[:5]:  # Show top 5
                        activity += f"  • {amount:.2f} TON to {destination[:6]}...{destination[-6:]}\n"
                        activity += f"    TX: {tx_hash}\n"

                if token_transfers:
                    activity += f"\nPotential {token_symbol} transfers ({len(token_transfers)}):\n"
                    for tx_hash, destination in token_transfers[:5]:  # Show top 5
                        activity += f"  • To: {destination[:6]}...{destination[-6:]}\n"
                        activity += f"    TX: {tx_hash}\n"

                suspicious_activities.append(activity)

        if not suspicious_activities:
            logging.info(f"No suspicious activity detected for {token_address}")
            return "No suspicious activity detected."
        else:
            logging.info(f"Suspicious activities found for {token_address}")
            response = f"Analysis for {token_symbol} ({token_address[:6]}...{token_address[-6:]}):\n\n"
            response += "Potential suspicious activities:\n\n"
            response += "\n---\n".join(suspicious_activities)
            return response
    except Exception as e:
        logging.error(f"Error in analyze_transactions: {e}")
        return f"An error occurred while analyzing transactions: {str(e)}"
    
@dp.callback_query_handler(lambda c: c.data.startswith('scan_holder|'))
async def handle_scan_holder(callback_query: types.CallbackQuery):
    try:
        _, token_address, holder_index = callback_query.data.split('|')
        holder_index = int(holder_index) - 1
        
        logging.info(f"\n--- API Call Results for Token: {token_address}, Holder Index: {holder_index} ---")
        
        token_info = await get_token_info(token_address)
        logging.info(f"\nToken Info: {json.dumps(token_info, indent=2)}")
        
        extended_info = await get_token_info_extended(token_address)
        logging.info(f"\nExtended Info: {json.dumps(extended_info, indent=2)}")
        
        holders = await fetch_token_holders(token_address)
        logging.info(f"\nHolders Info: {json.dumps(holders, indent=2)}")
        
        if not token_info or not extended_info or not holders or holder_index >= len(holders):
            await callback_query.answer("❌ Failed to fetch information.", show_alert=True)
            logging.error("❌ Failed to fetch complete information.")
            return
        
        holder_address = holders[holder_index]['owner']['address']
        holder_info = holders[holder_index]
        logging.info(f"\nSelected Holder Info: {json.dumps(holder_info, indent=2)}")
        
        recent_transactions = await get_recent_transactions(holder_address)
        logging.info(f"\nRecent Transactions: {json.dumps(recent_transactions, indent=2)}")
        
        token_symbol = token_info.get('metadata', {}).get('symbol', '')
        current_price = float(extended_info['price']) if extended_info['price'] else 0
        total_supply = int(token_info.get('total_supply', '1'))
        balance = int(holder_info.get('balance', 0))
        balance_percent = (balance / total_supply) * 100 if total_supply else 0
        wallet_value_usd = balance * current_price
        
        response_message = (
            f"📍 *Address:* [{holder_address[:6]}...{holder_address[-6:]}](https://tonviewer.com/{holder_address})\n"
            f"💰 *Balance:* `{format_large_number(balance)}` {token_symbol}\n"
            f"💵 *Value:* ~$`{format_large_number(wallet_value_usd)}`\n"
            f"📊 *Percentage:* `{balance_percent:.2f}%` of total supply\n\n"
            f"💲 *Token Info:*\n"
            f"├─ *Price:* ${extended_info['price']}\n"
            f"├─ *Market Cap:* ${format_large_number(extended_info['market_cap'])}\n"
            f"├─ *24h Volume:* ${format_large_number(extended_info['volume_24h'])}\n"
            f"└─ *24h Change:* {extended_info['price_change_24h']}%\n\n"
            f"🔄 *Recent Transactions:*\n"
        )
        
        if recent_transactions:
            for tx in recent_transactions[:5]:
                tx_type = "IN" if tx.get('in_msg', {}).get('source') else "OUT"
                amount = tx.get('in_msg', {}).get('value', 0) if tx_type == "IN" else tx.get('out_msgs', [{}])[0].get('value', 0)
                amount = float(amount) / 1e9
                timestamp = datetime.fromtimestamp(tx.get('utime', 0)).strftime('%Y-%m-%d %H:%M:%S')
                tx_hash = tx.get('transaction_id', {}).get('hash', '')
                tx_link = f"https://tonviewer.com/transaction/{tx_hash}"
                
                if tx_type == "IN":
                    from_address = tx.get('in_msg', {}).get('source', 'Unknown')
                    to_address = tx.get('in_msg', {}).get('destination', 'Unknown')
                    emoji = "🟢"
                else:
                    from_address = tx.get('out_msgs', [{}])[0].get('source', 'Unknown')
                    to_address = tx.get('out_msgs', [{}])[0].get('destination', 'Unknown')
                    emoji = "🔴"
                
                short_from = f"{from_address[:6]}...{from_address[-6:]}" if from_address != 'Unknown' else 'Unknown'
                short_to = f"{to_address[:6]}...{to_address[-6:]}" if to_address != 'Unknown' else 'Unknown'
                
                response_message += (
                    f"{emoji} *{tx_type}:* `{amount:.2f} TON`\n"
                    f"├─⏰ *Time:* `{timestamp}`\n"
                    f"├─👤 *From:* `{short_from}`\n"
                    f"├─👥 *To:* `{short_to}`\n"
                    f"└─🔗 [View Transaction]({tx_link})\n\n"
                )
        else:
            response_message += "❌ No recent transactions found.\n"
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🔍 Analyze Suspicious Activity", callback_data=f"analyze|{token_address}|{holder_index+1}"))
        keyboard.add(InlineKeyboardButton("🔄 Refresh", callback_data=f"scan_holder|{token_address}|{holder_index+1}"))
        keyboard.add(InlineKeyboardButton("🔙 Back to Holders", callback_data=f"holders|{token_address}"))
        
        try:
            await callback_query.message.edit_text(response_message, parse_mode='Markdown', reply_markup=keyboard, disable_web_page_preview=True)
        except aiogram.utils.exceptions.MessageNotModified:
            await callback_query.answer("Data is up to date!")
        
        logging.info("\n--- End of API Call Results ---\n")
        await callback_query.answer()
    except Exception as e:
        logging.error(f"Error in handle_scan_holder: {e}")

@dp.callback_query_handler(lambda c: c.data.startswith('analyze|'))
async def handle_analyze_suspicious(callback_query: types.CallbackQuery):
    try:
        _, token_address, holder_index = callback_query.data.split('|')
        holder_index = int(holder_index) - 1
        
        holders = await fetch_token_holders(token_address)
        if not holders or holder_index >= len(holders):
            await callback_query.answer("Failed to fetch holder information.", show_alert=True)
            return
        
        holder_address = holders[holder_index]['owner']['address']
        
        await callback_query.answer("Analyzing transactions... This may take a moment.")
        
        suspicious_activity = await analyze_transactions(holder_address)
        
        response_message = f"🚨 *Suspicious Activity Analysis for {holder_address[:6]}...{holder_address[-6:]}:*\n\n{suspicious_activity}\n"
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🔙 Back to Holder Info", callback_data=f"scan_holder|{token_address}|{holder_index+1}"))
        
        try:
            await callback_query.message.edit_text(response_message, parse_mode='Markdown', reply_markup=keyboard, disable_web_page_preview=True)
        except aiogram.utils.exceptions.MessageNotModified:
            await callback_query.answer("No changes in analysis results.")
    except Exception as e:
        logging.error(f"Error in handle_analyze_suspicious: {e}")

async def get_holder_info(holder_address, token_address):
    headers = {'Authorization': f'Bearer {TON_API_KEY}'}
    url = f"https://tonapi.io/v2/jettons/{token_address}/holders?addresses={holder_address}"
    try:
        async with aiohttp.ClientSession() as session:
            response = await session.get(url, headers=headers)
            if response.status == 200:
                data = await response.json()
                holder_data = data.get('addresses', [])[0] if data.get('addresses') else None
                return holder_data
            else:
                logging.error(f"Failed to fetch holder data: {response.status}")
                return None
    except Exception as e:
        logging.error(f"Error in get_holder_info: {e}")
        return None

async def get_recent_transactions(holder_address, limit=100):
    url = f"https://toncenter.com/api/v2/getTransactions?address={holder_address}&limit={limit}&to_lt=0&archival=false"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('result', [])
                else:
                    logging.error(f"Failed to fetch transactions: {response.status}")
                    return []
    except Exception as e:
        logging.error(f"Error fetching transactions: {e}")
        return []
    
async def get_holder_info(holder_address, token_address):
    # Obtenir les informations du holder pour le token spécifique
    headers = {'Authorization': f'Bearer {TON_API_KEY}'}
    url = f"https://tonapi.io/v2/jettons/{token_address}/holders?addresses={holder_address}"
    logging.info(f"Fetching holder info for address {holder_address} and token {token_address}")
    try:
        async with aiohttp.ClientSession() as session:
            response = await session.get(url, headers=headers)
            if response.status == 200:
                data = await response.json()
                holder_data = data.get('addresses', [])[0] if data.get('addresses') else None
                logging.info(f"Successfully fetched holder data for {holder_address}")
                return holder_data
            else:
                logging.error(f"Failed to fetch holder data: {response.status}")
                return None
    except Exception as e:
        logging.error(f"Error in get_holder_info: {str(e)}")
        return None

async def get_recent_transactions(holder_address, limit=100):
    url = f"https://toncenter.com/api/v2/getTransactions?address={holder_address}&limit={limit}&to_lt=0&archival=false"
    logging.info(f"Fetching recent transactions for address {holder_address}")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logging.info(f"Successfully fetched transactions for {holder_address}")
                    return data.get('result', [])
                else:
                    logging.error(f"Failed to fetch transactions: {response.status}")
                    return []
        except Exception as e:
            logging.error(f"Error fetching transactions: {str(e)}")
            return []

def track_usage(command_name):
    current_date = date.today().isoformat()
    filename = f"{command_name}_usage.txt"
    logging.info(f"Tracking usage for command: {command_name}")
    try:
        # Read existing data
        with open(filename, 'r+') as file:
            lines = file.readlines()
            last_line = lines[-1].strip() if lines else ""
            last_date, last_count = last_line.split(',') if last_line else (None, 0)
           
            if last_date == current_date:
                # Update current date's count
                new_count = int(last_count) + 1
                lines[-1] = f"{current_date},{new_count}\n"
            else:
                # Add new date with count 1
                lines.append(f"{current_date},1\n")
           
            # Write back to file
            file.seek(0)
            file.writelines(lines)
            file.truncate()
        logging.info(f"Usage tracked successfully for {command_name}")
    except FileNotFoundError:
        # If file doesn't exist, create it and add today's date with count 1
        with open(filename, 'w') as file:
            file.write(f"{current_date},1\n")
        logging.info(f"Created new usage file for {command_name}")
    except Exception as e:
        logging.error(f"Error tracking usage for {command_name}: {str(e)}")

def show_usage_stats(command_name):
    filename = f"{command_name}_usage.txt"
    logging.info(f"Showing usage stats for command: {command_name}")
    try:
        with open(filename, 'r') as file:
            logging.info(f"Usage stats for {command_name}:")
            for line in file:
                date, count = line.strip().split(',')
                logging.info(f"Date: {date}, Count: {count}")
    except FileNotFoundError:
        logging.info(f"No usage data available for {command_name}")
    except Exception as e:
        logging.error(f"Error showing usage stats for {command_name}: {str(e)}")

if __name__ == '__main__':
    logging.info("Starting the bot")
    executor.start_polling(dp, skip_updates=True)