#!/usr/bin/env python3
"""
Simple HTTP server for serving real-time crypto data
Compatible with WebContainer environment
"""

import json
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests
from typing import Dict, Any

class CryptoDataHandler(BaseHTTPRequestHandler):
    # Class variable to store latest data
    latest_data = {
        'symbol': 'BTCUSDT',
        'price': '0.00',
        'priceChange': '0.00',
        'priceChangePercent': '0.00',
        'volume': '0.00',
        'high': '0.00',
        'low': '0.00',
        'timestamp': int(time.time() * 1000)
    }
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/ticker':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            
            # Return latest data
            response_data = {
                'success': True,
                'data': self.latest_data
            }
            self.wfile.write(json.dumps(response_data).encode())
            
        elif parsed_path.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            health_data = {
                'status': 'healthy',
                'timestamp': int(time.time() * 1000)
            }
            self.wfile.write(json.dumps(health_data).encode())
            
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, format, *args):
        """Override to reduce log noise"""
        pass

class DataUpdater:
    """Updates crypto data from Binance API"""
    
    def __init__(self):
        self.running = False
        self.thread = None
    
    def start(self):
        """Start the data update thread"""
        self.running = True
        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()
        print("Data updater started")
    
    def stop(self):
        """Stop the data update thread"""
        self.running = False
        if self.thread:
            self.thread.join()
        print("Data updater stopped")
    
    def _update_loop(self):
        """Main update loop"""
        while self.running:
            try:
                self._fetch_and_update_data()
                time.sleep(1)  # Update every second
            except Exception as e:
                print(f"Error updating data: {e}")
                time.sleep(5)  # Wait longer on error
    
    def _fetch_and_update_data(self):
        """Fetch data from Binance API and update class variable"""
        try:
            # Binance 24hr ticker API
            url = "https://api.binance.com/api/v3/ticker/24hr"
            params = {"symbol": "BTCUSDT"}
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Update the class variable
            CryptoDataHandler.latest_data = {
                'symbol': data['symbol'],
                'price': data['lastPrice'],
                'priceChange': data['priceChange'],
                'priceChangePercent': data['priceChangePercent'],
                'volume': data['volume'],
                'high': data['highPrice'],
                'low': data['lowPrice'],
                'timestamp': int(time.time() * 1000)
            }
            
            print(f"Updated: {data['symbol']} = ${data['lastPrice']} ({data['priceChangePercent']}%)")
            
        except requests.exceptions.RequestException as e:
            print(f"Network error: {e}")
        except Exception as e:
            print(f"Data fetch error: {e}")

def run_server(port=8000):
    """Run the HTTP server"""
    print(f"Starting crypto data server on port {port}")
    
    # Start data updater
    updater = DataUpdater()
    updater.start()
    
    try:
        server = HTTPServer(('', port), CryptoDataHandler)
        print(f"Server running at http://localhost:{port}")
        print("Available endpoints:")
        print(f"  - http://localhost:{port}/api/ticker")
        print(f"  - http://localhost:{port}/health")
        
        server.serve_forever()
        
    except KeyboardInterrupt:
        print("\nShutting down server...")
        updater.stop()
        server.shutdown()
        print("Server stopped")
    except Exception as e:
        print(f"Server error: {e}")
        updater.stop()

if __name__ == "__main__":
    run_server()