package services

import (
	"fmt"
	"net"
	"os/exec"
	"plato-sdk/utils"
	"strings"
	"sync"
)

// ProxyTunnelService manages proxytunnel connections
type ProxyTunnelService struct {
	client    ClientInterface
	tunnels   map[string]*ProxyTunnel // key: tunnel ID
	tunnelsMu sync.Mutex
	nextID    int
}

// ProxyTunnel represents an active proxytunnel connection
type ProxyTunnel struct {
	ID         string
	LocalPort  int
	RemotePort int
	PublicID   string
	cmd        *exec.Cmd
}

// ProxyConfig holds proxy server configuration
type ProxyConfig struct {
	Server string
	Secure bool
}

// NewProxyTunnelService creates a new ProxyTunnel service
func NewProxyTunnelService(client ClientInterface) *ProxyTunnelService {
	return &ProxyTunnelService{
		client:  client,
		tunnels: make(map[string]*ProxyTunnel),
	}
}

// GetProxyConfig determines proxy configuration based on base URL
func GetProxyConfig(baseURL string) ProxyConfig {
	if strings.Contains(baseURL, "localhost:8080") {
		return ProxyConfig{
			Server: "localhost:8888",
			Secure: false,
		}
	}

	// Extract subdomain from base URL for plato.so domains
	if strings.Contains(baseURL, "plato.so") {
		parts := strings.Split(baseURL, ".")
		if len(parts) >= 3 {
			subdomain := strings.TrimPrefix(parts[0], "https://")
			subdomain = strings.TrimPrefix(subdomain, "http://")
			return ProxyConfig{
				Server: fmt.Sprintf("%s.proxy.plato.so:9000", subdomain),
				Secure: true,
			}
		}
		return ProxyConfig{
			Server: "proxy.plato.so:9000",
			Secure: true,
		}
	}

	// Default
	return ProxyConfig{
		Server: "proxy.plato.so:9000",
		Secure: true,
	}
}

// findFreePort finds an available local port
func findFreePort() (int, error) {
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		return 0, err
	}
	defer listener.Close()
	return listener.Addr().(*net.TCPAddr).Port, nil
}

// Start starts a new proxytunnel connection
// Returns tunnel ID, local port, and error
func (s *ProxyTunnelService) Start(publicID string, remotePort int, localPort int) (string, int, error) {
	s.tunnelsMu.Lock()
	defer s.tunnelsMu.Unlock()

	// Find proxytunnel binary
	proxytunnelPath, err := utils.FindProxytunnelPath()
	if err != nil {
		return "", 0, fmt.Errorf("proxytunnel not found: %w", err)
	}

	// If local port is 0, find a free port
	if localPort == 0 {
		localPort, err = findFreePort()
		if err != nil {
			return "", 0, fmt.Errorf("failed to find free port: %w", err)
		}
	}

	// Get proxy configuration
	proxyConfig := GetProxyConfig(s.client.GetBaseURL())

	// Build proxytunnel command arguments
	args := []string{}
	if proxyConfig.Secure {
		args = append(args, "-E")
	}
	args = append(args,
		"-p", proxyConfig.Server,
		"-P", fmt.Sprintf("%s@%d:newpass", publicID, remotePort),
		"-d", fmt.Sprintf("127.0.0.1:%d", remotePort),
		"-a", fmt.Sprintf("%d", localPort),
		"--no-check-certificate",
	)

	// Create command
	cmd := exec.Command(proxytunnelPath, args...)

	// Start the process
	if err := cmd.Start(); err != nil {
		return "", 0, fmt.Errorf("failed to start proxytunnel: %w", err)
	}

	// Generate tunnel ID
	s.nextID++
	tunnelID := fmt.Sprintf("tunnel_%d", s.nextID)

	// Store tunnel info
	s.tunnels[tunnelID] = &ProxyTunnel{
		ID:         tunnelID,
		LocalPort:  localPort,
		RemotePort: remotePort,
		PublicID:   publicID,
		cmd:        cmd,
	}

	return tunnelID, localPort, nil
}

// Stop stops a proxytunnel connection
func (s *ProxyTunnelService) Stop(tunnelID string) error {
	s.tunnelsMu.Lock()
	defer s.tunnelsMu.Unlock()

	tunnel, exists := s.tunnels[tunnelID]
	if !exists {
		return fmt.Errorf("tunnel %s not found", tunnelID)
	}

	// Kill the process
	if tunnel.cmd != nil && tunnel.cmd.Process != nil {
		if err := tunnel.cmd.Process.Kill(); err != nil {
			return fmt.Errorf("failed to kill proxytunnel process: %w", err)
		}
		// Wait for process to exit
		_ = tunnel.cmd.Wait()
	}

	// Remove from map
	delete(s.tunnels, tunnelID)

	return nil
}

// StopAll stops all active tunnels
func (s *ProxyTunnelService) StopAll() {
	s.tunnelsMu.Lock()
	defer s.tunnelsMu.Unlock()

	for _, tunnel := range s.tunnels {
		if tunnel.cmd != nil && tunnel.cmd.Process != nil {
			_ = tunnel.cmd.Process.Kill()
			_ = tunnel.cmd.Wait()
		}
	}

	s.tunnels = make(map[string]*ProxyTunnel)
}

// List returns all active tunnels
func (s *ProxyTunnelService) List() []*ProxyTunnel {
	s.tunnelsMu.Lock()
	defer s.tunnelsMu.Unlock()

	result := make([]*ProxyTunnel, 0, len(s.tunnels))
	for _, tunnel := range s.tunnels {
		result = append(result, tunnel)
	}
	return result
}

// Get returns info about a specific tunnel
func (s *ProxyTunnelService) Get(tunnelID string) (*ProxyTunnel, error) {
	s.tunnelsMu.Lock()
	defer s.tunnelsMu.Unlock()

	tunnel, exists := s.tunnels[tunnelID]
	if !exists {
		return nil, fmt.Errorf("tunnel %s not found", tunnelID)
	}

	return tunnel, nil
}
