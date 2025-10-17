#!/usr/bin/env python3
"""
Truputi Server - stateless, concurrent network throughput measurement
Runs in container, reads PSK from environment variable
"""

import socket
import socketserver
import threading
import os
import json
import time
import sys


# Buffer size for data transfers
BUFFER_SIZE = 64 * 1024  # 64KB chunks


class ThroughputHandler(socketserver.BaseRequestHandler):
    """Handler for each client connection"""

    def handle(self):
        """Handle a single client connection"""
        client_addr = self.request.getpeername()
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Connection from {client_addr}", flush=True)

        try:
            # Step 1: Receive and validate PSK
            if not self.authenticate():
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Authentication failed from {client_addr}", flush=True)
                return

            # Step 2: Receive test parameters
            params = self.receive_params()
            if not params:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Invalid parameters from {client_addr}", flush=True)
                return

            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Test started: {params['mode']} mode, "
                  f"{params['duration']}s, {params['streams']} stream(s) from {client_addr}", flush=True)

            # Step 3: Send acknowledgment
            self.request.sendall(b'OK\n')

            # Step 4: Execute the test
            if params['mode'] == 'download':
                # Server sends data to client
                self.handle_download(params['duration'])
            elif params['mode'] == 'upload':
                # Server receives data from client
                self.handle_upload(params['duration'])

            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Test completed from {client_addr}", flush=True)

        except Exception as e:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error handling {client_addr}: {e}", flush=True)
        finally:
            try:
                self.request.close()
            except:
                pass

    def authenticate(self):
        """Authenticate client using PSK"""
        try:
            # Receive PSK from client (max 256 bytes)
            psk_data = self.request.recv(256).decode('utf-8').strip()

            # Get expected PSK from environment
            expected_psk = os.environ.get('TRUPUTI_PSK', '')

            if not expected_psk:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] WARNING: No PSK configured in environment!", flush=True)
                self.request.sendall(b'ERROR: Server not configured\n')
                return False

            if psk_data == expected_psk:
                self.request.sendall(b'AUTH_OK\n')
                return True
            else:
                self.request.sendall(b'AUTH_FAILED\n')
                return False

        except Exception as e:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Authentication error: {e}", flush=True)
            return False

    def receive_params(self):
        """Receive test parameters from client"""
        try:
            # Receive JSON parameters (max 1KB)
            params_data = self.request.recv(1024).decode('utf-8').strip()
            params = json.loads(params_data)

            # Validate parameters
            if 'mode' not in params or params['mode'] not in ['upload', 'download']:
                return None
            if 'duration' not in params or params['duration'] <= 0:
                return None
            if 'streams' not in params or params['streams'] <= 0:
                return None

            return params

        except Exception as e:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Parameter parsing error: {e}", flush=True)
            return None

    def handle_download(self, duration):
        """Handle download test - server sends data to client"""
        # Prepare data buffer (random-ish data)
        data = b'X' * BUFFER_SIZE

        end_time = time.time() + duration

        try:
            while time.time() < end_time:
                self.request.sendall(data)
        except (BrokenPipeError, ConnectionResetError, socket.error):
            # Client disconnected, that's fine
            pass

    def handle_upload(self, duration):
        """Handle upload test - server receives data from client"""
        # Set socket timeout to 1 second to avoid blocking too long
        self.request.settimeout(1.0)

        end_time = time.time() + duration

        try:
            while time.time() < end_time:
                try:
                    data = self.request.recv(BUFFER_SIZE)
                    if not data:
                        break
                except socket.timeout:
                    # Timeout is expected, continue checking time
                    continue
        except socket.error:
            # Connection issue, that's fine
            pass
        finally:
            # Reset to blocking mode
            try:
                self.request.settimeout(None)
            except:
                pass


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """TCP server with threading support for concurrent connections"""
    allow_reuse_address = True
    daemon_threads = True


def main():
    """Main server entry point"""
    # Check for PSK in environment
    if not os.environ.get('TRUPUTI_PSK'):
        print("ERROR: TRUPUTI_PSK environment variable not set!", file=sys.stderr)
        print("Please set it before starting the server:", file=sys.stderr)
        print("  export TRUPUTI_PSK='your-secret-key'", file=sys.stderr)
        sys.exit(1)

    # Server configuration
    host = '0.0.0.0'  # Listen on all interfaces
    port = int(os.environ.get('TRUPUTI_PORT', '32201'))

    print(f"Starting Truputi server on {host}:{port}")
    print(f"PSK authentication enabled")
    print(f"Ready for concurrent connections...\n")

    try:
        server = ThreadedTCPServer((host, port), ThroughputHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()
        print("Server stopped.")
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
