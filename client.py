#!/usr/bin/env python3
"""
Truputi Client - Network throughput measurement client
Measures download and upload speeds with parallel TCP streams
"""

import socket
import threading
import time
import json
import argparse
import sys


# Buffer size for data transfers
BUFFER_SIZE = 64 * 1024  # 64KB chunks


class ThroughputStream:
    """Handles a single TCP stream for throughput measurement"""

    def __init__(self, server_host, server_port, psk, source_ip, mode, duration, stream_id):
        self.server_host = server_host
        self.server_port = server_port
        self.psk = psk
        self.source_ip = source_ip
        self.mode = mode
        self.duration = duration
        self.stream_id = stream_id
        self.bytes_transferred = 0
        self.error = None
        self.sock = None

    def recv_line(self, max_length=1024):
        """Receive data until newline character"""
        buffer = b''
        while len(buffer) < max_length:
            char = self.sock.recv(1)
            if not char:
                break
            buffer += char
            if char == b'\n':
                break
        return buffer.decode('utf-8').strip()

    def run(self):
        """Execute the throughput test for this stream"""
        try:
            # Create socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, BUFFER_SIZE * 2)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, BUFFER_SIZE * 2)

            # Bind to source IP if specified
            if self.source_ip:
                self.sock.bind((self.source_ip, 0))

            # Connect to server
            self.sock.connect((self.server_host, self.server_port))

            # Step 1: Authenticate
            self.sock.sendall(f"{self.psk}\n".encode('utf-8'))
            auth_response = self.recv_line()

            if auth_response != 'AUTH_OK':
                self.error = f"Authentication failed: {auth_response}"
                return

            # Step 2: Send test parameters
            params = {
                'mode': self.mode,
                'duration': self.duration,
                'streams': 1  # Each stream reports as 1
            }
            self.sock.sendall(f"{json.dumps(params)}\n".encode('utf-8'))

            # Step 3: Wait for acknowledgment
            ack = self.recv_line()
            if ack != 'OK':
                self.error = f"Server rejected test: {ack}"
                return

            # Step 4: Execute the test
            if self.mode == 'download':
                self.measure_download()
            elif self.mode == 'upload':
                self.measure_upload()

        except Exception as e:
            self.error = str(e)
        finally:
            if self.sock:
                try:
                    self.sock.close()
                except:
                    pass

    def measure_download(self):
        """Measure download speed - receive data from server"""
        end_time = time.time() + self.duration
        self.bytes_transferred = 0

        try:
            while time.time() < end_time:
                data = self.sock.recv(BUFFER_SIZE)
                if not data:
                    break
                self.bytes_transferred += len(data)
        except socket.error as e:
            # Connection error
            self.error = f"Download error: {e}"

    def measure_upload(self):
        """Measure upload speed - send data to server"""
        # Prepare data buffer
        data = b'Y' * BUFFER_SIZE

        end_time = time.time() + self.duration
        self.bytes_transferred = 0

        try:
            while time.time() < end_time:
                self.sock.sendall(data)
                self.bytes_transferred += len(data)
        except (BrokenPipeError, ConnectionResetError, socket.error) as e:
            # Connection error - this can happen when server closes first
            # Only report as error if we haven't transferred any data
            if self.bytes_transferred == 0:
                self.error = f"Upload error: {e}"
            # Otherwise, it's expected behavior at end of test
            pass


class ThroughputClient:
    """Main client for running throughput tests"""

    def __init__(self, server, port, psk, source_ip=None, duration=10, streams=1, debug=False):
        self.server = server
        self.port = port
        self.psk = psk
        self.source_ip = source_ip
        self.duration = duration
        self.streams = streams
        self.debug = debug

    def run_test(self, mode):
        """Run a throughput test in the specified mode (upload/download)"""
        start_time = time.time()

        # Create stream objects
        stream_objects = []
        for i in range(self.streams):
            stream = ThroughputStream(
                self.server, self.port, self.psk, self.source_ip,
                mode, self.duration, i
            )
            stream_objects.append(stream)

        # Create threads for each stream
        threads = []
        for stream in stream_objects:
            thread = threading.Thread(target=stream.run)
            threads.append(thread)

        # Start all threads simultaneously
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        end_time = time.time()
        actual_duration = end_time - start_time

        # Collect results
        total_bytes = 0
        errors = []

        for i, stream in enumerate(stream_objects):
            if stream.error:
                errors.append(f"Stream {i}: {stream.error}")
            else:
                total_bytes += stream.bytes_transferred

        # Calculate throughput in bits per second
        if actual_duration > 0:
            throughput_bps = (total_bytes * 8) / actual_duration
        else:
            throughput_bps = 0

        return {
            'mode': mode,
            'streams': self.streams,
            'duration_requested': self.duration,
            'duration_actual': round(actual_duration, 3),
            'bytes_transferred': total_bytes,
            'throughput_bps': int(throughput_bps),
            'throughput_mbps': round(throughput_bps / 1_000_000, 2),
            'errors': errors if errors else None
        }

    def run_full_test(self):
        """Run both upload and download tests"""
        results = {
            'server': self.server,
            'port': self.port,
            'source_ip': self.source_ip,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        }

        # Run download test
        if self.debug:
            print(f"Running download test ({self.streams} stream(s), {self.duration}s)...", file=sys.stderr)
        results['download'] = self.run_test('download')

        # Small pause between tests
        time.sleep(0.5)

        # Run upload test
        if self.debug:
            print(f"Running upload test ({self.streams} stream(s), {self.duration}s)...", file=sys.stderr)
        results['upload'] = self.run_test('upload')

        return results


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Truputi - Network throughput measurement client',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s --server 192.168.1.100 --psk mysecret
  %(prog)s --server speedtest.example.com --psk mysecret --source 10.0.0.5 --duration 15
  %(prog)s --server 192.168.1.100 --psk mysecret --streams 4 --duration 20
        '''
    )

    parser.add_argument('--server', required=True,
                        help='Server hostname or IP address')
    parser.add_argument('--port', type=int, default=32201,
                        help='Server port (default: 32201)')
    parser.add_argument('--psk', required=True,
                        help='Pre-shared key for authentication')
    parser.add_argument('--source', dest='source_ip', default=None,
                        help='Source IP address to bind to (optional)')
    parser.add_argument('--duration', type=int, default=10,
                        help='Test duration in seconds (default: 10, max: 20)')
    parser.add_argument('--streams', type=int, default=1,
                        help='Number of parallel TCP streams (default: 1)')
    parser.add_argument('--mode', choices=['download', 'upload', 'both'], default='both',
                        help='Test mode: download, upload, or both (default: both)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug output with detailed connection information')

    args = parser.parse_args()

    # Validate duration
    if args.duration > 20:
        if args.debug:
            print("WARNING: Duration exceeds 20 seconds, capping to 20s", file=sys.stderr)
        args.duration = 20
    if args.duration <= 0:
        print("ERROR: Duration must be positive", file=sys.stderr)
        sys.exit(1)

    # Validate streams
    if args.streams <= 0:
        print("ERROR: Streams must be positive", file=sys.stderr)
        sys.exit(1)
    if args.streams > 16:
        if args.debug:
            print("WARNING: High number of streams may cause issues", file=sys.stderr)

    try:
        # Create client
        client = ThroughputClient(
            args.server, args.port, args.psk,
            args.source_ip, args.duration, args.streams, args.debug
        )

        # Debug: Connection info
        if args.debug:
            print(f"Connecting to {args.server}:{args.port}", file=sys.stderr)
            if args.source_ip:
                print(f"Binding to source IP: {args.source_ip}", file=sys.stderr)
            print(f"Test parameters: {args.streams} stream(s), {args.duration}s duration", file=sys.stderr)
            print("", file=sys.stderr)

        # Run test(s)
        if args.mode == 'both':
            results = client.run_full_test()
        else:
            if args.debug:
                print(f"Running {args.mode} test ({args.streams} stream(s), {args.duration}s)...", file=sys.stderr)
            results = {
                'server': args.server,
                'port': args.port,
                'source_ip': args.source_ip,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                args.mode: client.run_test(args.mode)
            }

        # Output results as JSON
        print(json.dumps(results, indent=2))

        # Exit with error if there were any errors
        has_errors = False
        for key in ['download', 'upload']:
            if key in results and results[key].get('errors'):
                has_errors = True
                break

        sys.exit(1 if has_errors else 0)

    except KeyboardInterrupt:
        if args.debug:
            print("\nTest interrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
