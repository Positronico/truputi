# Truputi

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Docker Build](https://github.com/Positronico/truputi/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/Positronico/truputi/actions/workflows/docker-publish.yml)

A lightweight Python-based network throughput measurement system using only built-in libraries. Truputi is designed for measuring TCP throughput between client and server components with support for parallel streams.

**Truputi** (from Sanskrit: तृप्ति, meaning "satisfaction" or "fulfillment") - delivering complete network performance insights.

## Installation

No installation required! Truputi uses only Python built-in libraries. Simply clone and run:

```bash
git clone git@github.com:Positronico/truputi.git
cd truputi
chmod +x client.py server.py
```

## Features

- **Pure Python**: Uses only built-in libraries (no external dependencies)
- **TCP-based**: Reliable throughput measurements over TCP
- **Parallel Streams**: Support for multiple concurrent TCP streams
- **Bidirectional**: Measures both download and upload speeds
- **Stateless Server**: No persistent storage required, ideal for Kubernetes
- **Concurrent**: Server handles multiple clients simultaneously
- **Authenticated**: PSK-based authentication prevents abuse
- **JSON Output**: Machine-readable results from client

## Components

### Server (`server.py`)
- Handles multiple concurrent client connections
- PSK authentication via environment variable
- Stateless design (no data persistence)
- Docker-ready for container deployment

### Client (`client.py`)
- Configurable source IP binding (multi-interface support)
- Parallel TCP stream support
- Configurable test duration (max 20s by default)
- JSON-formatted output with throughput in bps

## Quick Start

### Using Pre-built Container Images

Pre-built images are automatically published to GitHub Container Registry on every push to `main` and for all tagged releases.

**Available tags:**
- `latest` - Latest build from main branch
- `v*.*.*` - Semantic version tags (e.g., `v1.0.0`, `v1.0`, `v1`)

```bash
# Pull the latest image
docker pull ghcr.io/positronico/truputi:latest

# Or pull a specific version
docker pull ghcr.io/positronico/truputi:v1.0.0

# Run the server
docker run -d \
  -p 32201:32201 \
  -e TRUPUTI_PSK="your-secret-key-here" \
  --name truputi-server \
  ghcr.io/positronico/truputi:latest
```

### Building the Server Container Locally

```bash
# Build the Docker image
docker build -t truputi-server:latest .

# Run the server
docker run -d \
  -p 32201:32201 \
  -e TRUPUTI_PSK="your-secret-key-here" \
  --name truputi-server \
  truputi-server:latest
```

### Running the Client

```bash
# Make client executable
chmod +x client.py

# Basic test (both upload and download)
./client.py --server 192.168.1.100 --psk your-secret-key-here

# Test with specific source IP
./client.py --server 192.168.1.100 --psk your-secret-key-here --source 10.0.0.5

# Test with parallel streams and custom duration
./client.py --server 192.168.1.100 --psk your-secret-key-here --streams 4 --duration 15

# Download only
./client.py --server 192.168.1.100 --psk your-secret-key-here --mode download

# Upload only
./client.py --server 192.168.1.100 --psk your-secret-key-here --mode upload

# Debug mode with detailed connection information
./client.py --server 192.168.1.100 --psk your-secret-key-here --debug
```

**Note:** By default, the client only outputs JSON results. Use `--debug` flag to see detailed connection information on stderr.

## Client Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--server` | Yes | - | Server hostname or IP address |
| `--psk` | Yes | - | Pre-shared key for authentication |
| `--port` | No | 32201 | Server port |
| `--source` | No | - | Source IP address to bind to |
| `--duration` | No | 10 | Test duration in seconds (max 20) |
| `--streams` | No | 1 | Number of parallel TCP streams |
| `--mode` | No | both | Test mode: `download`, `upload`, or `both` |
| `--debug` | No | false | Enable debug output with detailed connection info |

## Client Output Format

```json
{
  "server": "192.168.1.100",
  "port": 5201,
  "source_ip": null,
  "timestamp": "2025-10-17 14:30:45",
  "download": {
    "mode": "download",
    "streams": 1,
    "duration_requested": 10,
    "duration_actual": 10.002,
    "bytes_transferred": 125829120,
    "throughput_bps": 100663296,
    "throughput_mbps": 100.66,
    "errors": null
  },
  "upload": {
    "mode": "upload",
    "streams": 1,
    "duration_requested": 10,
    "duration_actual": 10.001,
    "bytes_transferred": 104857600,
    "throughput_bps": 83886080,
    "throughput_mbps": 83.89,
    "errors": null
  }
}
```

## Kubernetes Deployment

### Example Deployment YAML

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: truputi-server
  labels:
    app: truputi-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: truputi-server
  template:
    metadata:
      labels:
        app: truputi-server
    spec:
      containers:
      - name: truputi-server
        image: ghcr.io/positronico/truputi:latest
        ports:
        - containerPort: 32201
          name: truputi
          protocol: TCP
        env:
        - name: TRUPUTI_PSK
          valueFrom:
            secretKeyRef:
              name: truputi-secret
              key: psk
        resources:
          requests:
            memory: "64Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "1000m"
        livenessProbe:
          tcpSocket:
            port: 32201
          initialDelaySeconds: 5
          periodSeconds: 10
        readinessProbe:
          tcpSocket:
            port: 32201
          initialDelaySeconds: 5
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: truputi-server
spec:
  type: LoadBalancer
  selector:
    app: truputi-server
  ports:
  - port: 32201
    targetPort: 32201
    protocol: TCP
    name: truputi
---
apiVersion: v1
kind: Secret
metadata:
  name: truputi-secret
type: Opaque
stringData:
  psk: "your-secret-key-here"
```

### Deploy to Kubernetes

```bash
# Apply the configuration
kubectl apply -f k8s-deployment.yaml

# Check the deployment
kubectl get pods -l app=truputi-server

# Get the service external IP
kubectl get svc truputi-server

# View logs
kubectl logs -l app=truputi-server --tail=50
```

## Build Process

### Docker Build

```bash
# Build the image
docker build -t truputi-server:latest .

# Tag for registry (replace with your registry)
docker tag truputi-server:latest myregistry.example.com/truputi-server:1.0.0

# Push to registry
docker push myregistry.example.com/truputi-server:1.0.0
```

### Local Testing (Without Docker)

```bash
# Start server locally
export TRUPUTI_PSK="test-secret"
python3 server.py

# In another terminal, run client
python3 client.py --server localhost --psk test-secret
```

## Security Considerations

1. **PSK Management**: Store the PSK in Kubernetes secrets, never in code or ConfigMaps
2. **Network Policies**: Use Kubernetes network policies to restrict access
3. **Resource Limits**: Set appropriate CPU/memory limits to prevent resource exhaustion
4. **Non-Root User**: Container runs as non-root user (UID 1000)
5. **Rate Limiting**: Consider implementing ingress rate limiting for production

## Architecture

### Protocol Flow

```
Client                          Server
  |                               |
  |------- Connect TCP ---------->|
  |                               |
  |-------- Send PSK ------------>|
  |<----- AUTH_OK/FAILED ---------|
  |                               |
  |--- Send Test Parameters ----->|
  |<---------- OK ----------------|
  |                               |
  |<===== Data Transfer =========>|
  |     (duration seconds)        |
  |                               |
  |------- Close TCP ------------>|
```

### Parallel Streams

When using multiple streams (`--streams N`), the client creates N independent TCP connections, each running the protocol above simultaneously. The total throughput is the sum of all streams.

## Troubleshooting

### Server Not Starting

```bash
# Check if PSK is set
docker exec truputi-server env | grep TRUPUTI_PSK

# Check logs
docker logs truputi-server
```

### Client Authentication Failed

```bash
# Verify PSK matches on both sides
# Server PSK is in TRUPUTI_PSK environment variable
# Client PSK is passed via --psk parameter
```

### Low Throughput

- Try increasing parallel streams: `--streams 4`
- Check network conditions between client and server
- Verify no bandwidth limitations on network path
- Check server CPU/memory usage

### Source IP Binding Issues

```bash
# List available network interfaces
ip addr show  # Linux
ifconfig      # macOS

# Use the correct IP from the desired interface
./client.py --server 192.168.1.100 --psk secret --source 10.0.0.5
```

## Performance Tuning

### Server

- Increase replicas in Kubernetes for higher concurrent client capacity
- Adjust CPU/memory limits based on usage patterns
- Use node affinity for network-optimized nodes

### Client

- Use multiple streams for higher throughput: `--streams 4`
- Adjust duration based on network stability
- Consider client system's network buffer sizes

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## License

MIT License - see the [LICENSE](LICENSE) file for details.

## Author

**Positronico**

## Acknowledgments

Truputi is designed as a simple, dependency-free network performance measurement tool suitable for deployment in containerized environments.
