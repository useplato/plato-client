// Package main provides C bindings for the Plato Sandbox SDK
package main

/*
#include <stdlib.h>
*/
import "C"
import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"time"
	"unsafe"

	plato "plato-sdk"
	"plato-sdk/models"
)

var clients = make(map[string]*plato.PlatoClient)
var nextID = 0
var heartbeatStoppers = make(map[string]chan struct{})
var debugLogger *log.Logger

func init() {
	// Check if debug logging is enabled via environment variable
	if os.Getenv("PLATO_DEBUG") != "" {
		debugLogger = log.New(os.Stderr, "[PLATO-GO] ", log.LstdFlags)
		debugLogger.Println("Debug logging enabled")
	}
}

func logDebug(format string, v ...interface{}) {
	if debugLogger != nil {
		debugLogger.Printf(format, v...)
	}
}

//export plato_new_client
func plato_new_client(baseURL *C.char, apiKey *C.char) *C.char {
	nextID++
	clientID := fmt.Sprintf("client_%d", nextID)

	client := plato.NewClient(
		C.GoString(apiKey),
		plato.WithBaseURL(C.GoString(baseURL)),
	)
	clients[clientID] = client

	return C.CString(clientID)
}

//export plato_create_sandbox
func plato_create_sandbox(clientID *C.char, configJSON *C.char, dataset *C.char, alias *C.char, artifactID *C.char, service *C.char) *C.char {
	client, ok := clients[C.GoString(clientID)]
	if !ok {
		return C.CString(fmt.Sprintf(`{"error": "invalid client ID"}`))
	}

	var config models.SimConfigDataset
	if err := json.Unmarshal([]byte(C.GoString(configJSON)), &config); err != nil {
		return C.CString(fmt.Sprintf(`{"error": "failed to parse config: %v"}`, err))
	}

	var aid *string
	if artifactID != nil && C.GoString(artifactID) != "" {
		s := C.GoString(artifactID)
		aid = &s
	}

	ctx := context.Background()
	sandbox, err := client.Sandbox.Create(
		ctx,
		&config,
		C.GoString(dataset),
		C.GoString(alias),
		aid,
		C.GoString(service),
	)
	if err != nil {
		return C.CString(fmt.Sprintf(`{"error": "%v"}`, err))
	}

	result, err := json.Marshal(sandbox)
	if err != nil {
		return C.CString(fmt.Sprintf(`{"error": "failed to marshal result: %v"}`, err))
	}

	// Start automatic heartbeat goroutine for this sandbox
	if sandbox.JobGroupId != "" {
		logDebug("Starting heartbeat for sandbox %s (job_group_id: %s)", sandbox.PublicId, sandbox.JobGroupId)
		startHeartbeat(client, sandbox.JobGroupId)
	}

	return C.CString(string(result))
}

// startHeartbeat starts a goroutine that sends periodic heartbeats for a sandbox
func startHeartbeat(client *plato.PlatoClient, jobGroupID string) {
	// Don't start if already running
	if _, exists := heartbeatStoppers[jobGroupID]; exists {
		logDebug("Heartbeat already running for job_group_id: %s", jobGroupID)
		return
	}

	stopChan := make(chan struct{})
	heartbeatStoppers[jobGroupID] = stopChan

	go func() {
		ticker := time.NewTicker(30 * time.Second)
		defer ticker.Stop()

		// Send initial heartbeat
		ctx := context.Background()
		logDebug("Sending initial heartbeat for job_group_id: %s", jobGroupID)
		err := client.Sandbox.SendHeartbeat(ctx, jobGroupID)
		if err != nil {
			logDebug("Initial heartbeat failed for %s: %v", jobGroupID, err)
		} else {
			logDebug("Initial heartbeat successful for %s", jobGroupID)
		}

		for {
			select {
			case <-ticker.C:
				// Send heartbeat
				ctx := context.Background()
				logDebug("Sending heartbeat for job_group_id: %s", jobGroupID)
				err := client.Sandbox.SendHeartbeat(ctx, jobGroupID)
				if err != nil {
					logDebug("Heartbeat failed for %s: %v", jobGroupID, err)
				} else {
					logDebug("Heartbeat successful for %s", jobGroupID)
				}
			case <-stopChan:
				// Stop signal received
				logDebug("Stopping heartbeat for job_group_id: %s", jobGroupID)
				delete(heartbeatStoppers, jobGroupID)
				return
			}
		}
	}()
}

//export plato_delete_sandbox
func plato_delete_sandbox(clientID *C.char, publicID *C.char) *C.char {
	client, ok := clients[C.GoString(clientID)]
	if !ok {
		return C.CString(`{"error": "invalid client ID"}`)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	// First get the sandbox to find its job_group_id
	publicIDStr := C.GoString(publicID)
	logDebug("Closing sandbox: %s", publicIDStr)
	sandbox, err := client.Sandbox.Get(ctx, publicIDStr)
	if err == nil && sandbox.JobGroupId != "" {
		// Stop heartbeat if running
		if stopChan, exists := heartbeatStoppers[sandbox.JobGroupId]; exists {
			logDebug("Stopping heartbeat for sandbox %s (job_group_id: %s)", publicIDStr, sandbox.JobGroupId)
			close(stopChan)
		}
	}

	if err := client.Sandbox.DeleteVM(ctx, C.GoString(publicID)); err != nil {
		return C.CString(fmt.Sprintf(`{"error": "%v"}`, err))
	}

	return C.CString(`{"success": true}`)
}

//export plato_create_snapshot
func plato_create_snapshot(clientID *C.char, publicID *C.char, requestJSON *C.char) *C.char {
	client, ok := clients[C.GoString(clientID)]
	if !ok {
		return C.CString(`{"error": "invalid client ID"}`)
	}

	var req models.CreateSnapshotRequest
	if err := json.Unmarshal([]byte(C.GoString(requestJSON)), &req); err != nil {
		return C.CString(fmt.Sprintf(`{"error": "failed to parse request: %v"}`, err))
	}

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	resp, err := client.Sandbox.CreateSnapshot(ctx, C.GoString(publicID), &req)
	if err != nil {
		return C.CString(fmt.Sprintf(`{"error": "%v"}`, err))
	}

	result, err := json.Marshal(resp)
	if err != nil {
		return C.CString(fmt.Sprintf(`{"error": "failed to marshal result: %v"}`, err))
	}

	return C.CString(string(result))
}

//export plato_create_snapshot_with_cleanup
func plato_create_snapshot_with_cleanup(clientID *C.char, publicID *C.char, jobGroupID *C.char, requestJSON *C.char, dbConfigJSON *C.char) *C.char {
	client, ok := clients[C.GoString(clientID)]
	if !ok {
		return C.CString(`{"error": "invalid client ID"}`)
	}

	var req models.CreateSnapshotRequest
	if err := json.Unmarshal([]byte(C.GoString(requestJSON)), &req); err != nil {
		return C.CString(fmt.Sprintf(`{"error": "failed to parse request: %v"}`, err))
	}

	// Parse DB config if provided (may be null/empty string)
	var dbConfig *models.DBConfig
	dbConfigStr := C.GoString(dbConfigJSON)
	if dbConfigStr != "" && dbConfigStr != "null" {
		var cfg models.DBConfig
		if err := json.Unmarshal([]byte(dbConfigStr), &cfg); err != nil {
			return C.CString(fmt.Sprintf(`{"error": "failed to parse db_config: %v"}`, err))
		}
		dbConfig = &cfg
	}

	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	logDebug("Creating snapshot with cleanup for publicID=%s, jobGroupID=%s", C.GoString(publicID), C.GoString(jobGroupID))
	resp, err := client.Sandbox.CreateSnapshotWithCleanup(ctx, C.GoString(publicID), C.GoString(jobGroupID), &req, dbConfig)
	if err != nil {
		logDebug("CreateSnapshotWithCleanup failed: %v", err)
		return C.CString(fmt.Sprintf(`{"error": "%v"}`, err))
	}

	logDebug("Snapshot created successfully: %s", resp.ArtifactId)
	result, err := json.Marshal(resp)
	if err != nil {
		return C.CString(fmt.Sprintf(`{"error": "failed to marshal result: %v"}`, err))
	}

	return C.CString(string(result))
}

//export plato_start_worker
func plato_start_worker(clientID *C.char, publicID *C.char, requestJSON *C.char) *C.char {
	client, ok := clients[C.GoString(clientID)]
	if !ok {
		return C.CString(`{"error": "invalid client ID"}`)
	}

	var req models.StartWorkerRequest
	if err := json.Unmarshal([]byte(C.GoString(requestJSON)), &req); err != nil {
		return C.CString(fmt.Sprintf(`{"error": "failed to parse request: %v"}`, err))
	}

	ctx := context.Background()

	resp, err := client.Sandbox.StartWorker(ctx, C.GoString(publicID), &req)
	if err != nil {
		return C.CString(fmt.Sprintf(`{"error": "%v"}`, err))
	}

	result, err := json.Marshal(resp)
	if err != nil {
		return C.CString(fmt.Sprintf(`{"error": "failed to marshal result: %v"}`, err))
	}

	return C.CString(string(result))
}

//export plato_list_simulators
func plato_list_simulators(clientID *C.char) *C.char {
	client, ok := clients[C.GoString(clientID)]
	if !ok {
		return C.CString(`{"error": "invalid client ID"}`)
	}

	ctx := context.Background()

	simulators, err := client.Simulator.List(ctx)
	if err != nil {
		return C.CString(fmt.Sprintf(`{"error": "%v"}`, err))
	}

	result, err := json.Marshal(simulators)
	if err != nil {
		return C.CString(fmt.Sprintf(`{"error": "failed to marshal result: %v"}`, err))
	}

	return C.CString(string(result))
}

//export plato_get_simulator_versions
func plato_get_simulator_versions(clientID *C.char, simulatorName *C.char) *C.char {
	client, ok := clients[C.GoString(clientID)]
	if !ok {
		return C.CString(`{"error": "invalid client ID"}`)
	}

	ctx := context.Background()

	versions, err := client.Simulator.GetVersions(ctx, C.GoString(simulatorName))
	if err != nil {
		return C.CString(fmt.Sprintf(`{"error": "%v"}`, err))
	}

	result, err := json.Marshal(versions)
	if err != nil {
		return C.CString(fmt.Sprintf(`{"error": "failed to marshal result: %v"}`, err))
	}

	return C.CString(string(result))
}

//export plato_monitor_operation
func plato_monitor_operation(clientID *C.char, correlationID *C.char, timeoutSeconds C.int) *C.char {
	client, ok := clients[C.GoString(clientID)]
	if !ok {
		return C.CString(`{"error": "invalid client ID"}`)
	}

	ctx := context.Background()
	timeout := time.Duration(timeoutSeconds) * time.Second

	err := client.Sandbox.MonitorOperation(ctx, C.GoString(correlationID), timeout)
	if err != nil {
		return C.CString(fmt.Sprintf(`{"error": "%v"}`, err))
	}

	return C.CString(`{"success": true, "status": "completed"}`)
}

//export plato_free_string
func plato_free_string(s *C.char) {
	C.free(unsafe.Pointer(s))
}

//export plato_gitea_get_credentials
func plato_gitea_get_credentials(clientID *C.char) *C.char {
	client, ok := clients[C.GoString(clientID)]
	if !ok {
		return C.CString(`{"error": "invalid client ID"}`)
	}

	logDebug("Getting Gitea credentials")
	ctx := context.Background()
	creds, err := client.Gitea.GetCredentials(ctx)
	if err != nil {
		logDebug("Failed to get Gitea credentials: %v", err)
		return C.CString(fmt.Sprintf(`{"error": "%v"}`, err))
	}

	logDebug("Got Gitea credentials for user: %s, org: %s", creds.Username, creds.OrgName)
	result, err := json.Marshal(creds)
	if err != nil {
		return C.CString(fmt.Sprintf(`{"error": "failed to marshal result: %v"}`, err))
	}

	return C.CString(string(result))
}

//export plato_gitea_list_simulators
func plato_gitea_list_simulators(clientID *C.char) *C.char {
	client, ok := clients[C.GoString(clientID)]
	if !ok {
		return C.CString(`{"error": "invalid client ID"}`)
	}

	logDebug("Listing Gitea simulators")
	ctx := context.Background()
	simulators, err := client.Gitea.ListSimulators(ctx)
	if err != nil {
		logDebug("Failed to list simulators: %v", err)
		return C.CString(fmt.Sprintf(`{"error": "%v"}`, err))
	}

	logDebug("Found %d simulators", len(simulators))
	result, err := json.Marshal(simulators)
	if err != nil {
		return C.CString(fmt.Sprintf(`{"error": "failed to marshal result: %v"}`, err))
	}

	return C.CString(string(result))
}

//export plato_gitea_get_simulator_repo
func plato_gitea_get_simulator_repo(clientID *C.char, simulatorID C.int) *C.char {
	client, ok := clients[C.GoString(clientID)]
	if !ok {
		return C.CString(`{"error": "invalid client ID"}`)
	}

	logDebug("Getting repository for simulator ID: %d", int(simulatorID))
	ctx := context.Background()
	repo, err := client.Gitea.GetSimulatorRepository(ctx, int(simulatorID))
	if err != nil {
		logDebug("Failed to get repository for simulator %d: %v", int(simulatorID), err)
		return C.CString(fmt.Sprintf(`{"error": "%v"}`, err))
	}

	logDebug("Got repository: %s (clone_url: %s)", repo.Name, repo.CloneURL)
	result, err := json.Marshal(repo)
	if err != nil {
		return C.CString(fmt.Sprintf(`{"error": "failed to marshal result: %v"}`, err))
	}

	return C.CString(string(result))
}

//export plato_gitea_create_simulator_repo
func plato_gitea_create_simulator_repo(clientID *C.char, simulatorID C.int) *C.char {
	client, ok := clients[C.GoString(clientID)]
	if !ok {
		return C.CString(`{"error": "invalid client ID"}`)
	}

	logDebug("Creating repository for simulator ID: %d", int(simulatorID))
	ctx := context.Background()
	repo, err := client.Gitea.CreateSimulatorRepository(ctx, int(simulatorID))
	if err != nil {
		logDebug("Failed to create repository for simulator %d: %v", int(simulatorID), err)
		return C.CString(fmt.Sprintf(`{"error": "%v"}`, err))
	}

	logDebug("Created repository: %s (clone_url: %s)", repo.Name, repo.CloneURL)
	result, err := json.Marshal(repo)
	if err != nil {
		return C.CString(fmt.Sprintf(`{"error": "failed to marshal result: %v"}`, err))
	}

	return C.CString(string(result))
}

//export plato_proxytunnel_start
func plato_proxytunnel_start(clientID *C.char, publicID *C.char, remotePort C.int, localPort C.int) *C.char {
	client, ok := clients[C.GoString(clientID)]
	if !ok {
		return C.CString(`{"error": "invalid client ID"}`)
	}

	logDebug("Starting proxytunnel: publicID=%s, remotePort=%d, localPort=%d", C.GoString(publicID), int(remotePort), int(localPort))

	tunnelID, actualLocalPort, err := client.ProxyTunnel.Start(
		C.GoString(publicID),
		int(remotePort),
		int(localPort),
	)
	if err != nil {
		logDebug("Failed to start proxytunnel: %v", err)
		return C.CString(fmt.Sprintf(`{"error": "%v"}`, err))
	}

	logDebug("Proxytunnel started: tunnelID=%s, localPort=%d", tunnelID, actualLocalPort)

	result := map[string]interface{}{
		"tunnel_id":  tunnelID,
		"local_port": actualLocalPort,
	}
	resultJSON, _ := json.Marshal(result)
	return C.CString(string(resultJSON))
}

//export plato_proxytunnel_stop
func plato_proxytunnel_stop(clientID *C.char, tunnelID *C.char) *C.char {
	client, ok := clients[C.GoString(clientID)]
	if !ok {
		return C.CString(`{"error": "invalid client ID"}`)
	}

	tidStr := C.GoString(tunnelID)
	logDebug("Stopping proxytunnel: tunnelID=%s", tidStr)

	err := client.ProxyTunnel.Stop(tidStr)
	if err != nil {
		logDebug("Failed to stop proxytunnel: %v", err)
		return C.CString(fmt.Sprintf(`{"error": "%v"}`, err))
	}

	logDebug("Proxytunnel stopped: tunnelID=%s", tidStr)
	return C.CString(`{"success": true}`)
}

//export plato_proxytunnel_list
func plato_proxytunnel_list(clientID *C.char) *C.char {
	client, ok := clients[C.GoString(clientID)]
	if !ok {
		return C.CString(`{"error": "invalid client ID"}`)
	}

	tunnels := client.ProxyTunnel.List()
	result, err := json.Marshal(tunnels)
	if err != nil {
		return C.CString(fmt.Sprintf(`{"error": "failed to marshal result: %v"}`, err))
	}

	return C.CString(string(result))
}

//export plato_gitea_push_to_hub
func plato_gitea_push_to_hub(clientID *C.char, serviceName *C.char, sourceDir *C.char) *C.char {
	client, ok := clients[C.GoString(clientID)]
	if !ok {
		return C.CString(`{"error": "invalid client ID"}`)
	}

	serviceNameStr := C.GoString(serviceName)
	sourceDirStr := C.GoString(sourceDir)
	logDebug("Pushing to hub: service=%s, sourceDir=%s", serviceNameStr, sourceDirStr)

	ctx := context.Background()
	result, err := client.Gitea.PushToHub(ctx, serviceNameStr, sourceDirStr)
	if err != nil {
		logDebug("Failed to push to hub: %v", err)
		return C.CString(fmt.Sprintf(`{"error": "%v"}`, err))
	}

	logDebug("Pushed to hub: branch=%s", result.BranchName)

	resultJSON, err := json.Marshal(result)
	if err != nil {
		return C.CString(fmt.Sprintf(`{"error": "failed to marshal result: %v"}`, err))
	}

	return C.CString(string(resultJSON))
}

//export plato_gitea_merge_to_main
func plato_gitea_merge_to_main(clientID *C.char, serviceName *C.char, branchName *C.char) *C.char {
	client, ok := clients[C.GoString(clientID)]
	if !ok {
		return C.CString(`{"error": "invalid client ID"}`)
	}

	serviceNameStr := C.GoString(serviceName)
	branchNameStr := C.GoString(branchName)
	logDebug("Merging to main: service=%s, branch=%s", serviceNameStr, branchNameStr)

	ctx := context.Background()
	gitHash, err := client.Gitea.MergeToMain(ctx, serviceNameStr, branchNameStr)
	if err != nil {
		logDebug("Failed to merge to main: %v", err)
		return C.CString(fmt.Sprintf(`{"error": "%v"}`, err))
	}

	logDebug("Merged to main: gitHash=%s", gitHash)

	result := map[string]string{
		"git_hash": gitHash,
	}
	resultJSON, _ := json.Marshal(result)
	return C.CString(string(resultJSON))
}

//export plato_setup_ssh
func plato_setup_ssh(clientID *C.char, baseURL *C.char, localPort C.int, jobPublicID *C.char, username *C.char, configJSON *C.char, dataset *C.char) *C.char {
	client, ok := clients[C.GoString(clientID)]
	if !ok {
		return C.CString(`{"error": "invalid client ID"}`)
	}

	baseURLStr := C.GoString(baseURL)
	publicIDStr := C.GoString(jobPublicID)
	usernameStr := C.GoString(username)
	datasetStr := C.GoString(dataset)
	port := int(localPort)

	// Parse config JSON
	var config models.SimConfigDataset
	if err := json.Unmarshal([]byte(C.GoString(configJSON)), &config); err != nil {
		return C.CString(fmt.Sprintf(`{"error": "failed to parse config: %v"}`, err))
	}

	logDebug("Setting up SSH for sandbox: publicID=%s, username=%s, port=%d", publicIDStr, usernameStr, port)

	ctx := context.Background()
	sshInfo, err := client.Sandbox.SetupSSHAndGetInfo(ctx, baseURLStr, port, publicIDStr, usernameStr, &config, datasetStr)
	if err != nil {
		logDebug("Failed to setup SSH: %v", err)
		return C.CString(fmt.Sprintf(`{"error": "%v"}`, err))
	}

	logDebug("SSH setup complete: command=%s", sshInfo.SSHCommand)

	result, err := json.Marshal(sshInfo)
	if err != nil {
		return C.CString(fmt.Sprintf(`{"error": "failed to marshal result: %v"}`, err))
	}

	return C.CString(string(result))
}

func main() {}
