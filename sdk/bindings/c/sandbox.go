// Package main provides C-compatible bindings for the Plato Sandbox SDK.
//
// This package exports sandbox operations as a C shared library that can be
// imported into Python, JavaScript, and other languages. It includes automatic
// heartbeat management to keep VMs alive.
package main

/*
#include <stdlib.h>
#include <string.h>

typedef struct {
    char* job_id;
    char* public_id;
    char* job_group_id;
    char* url;
    char* status;
    char* correlation_id;
} CSandbox;

typedef struct {
    char* error;
    int code;
} CError;

*/
import "C"
import (
	"context"
	"fmt"
	"runtime"
	"sync"
	"time"
	"unsafe"

	plato "plato-sdk"
	"plato-sdk/models"
	"google.golang.org/protobuf/encoding/protojson"
)


// Global state management
var (
	clients    = make(map[int64]*plato.PlatoClient)
	heartbeats = make(map[string]*heartbeatManager)
	clientMux  sync.RWMutex
	hbMux      sync.RWMutex
	nextID     int64 = 1
)

// heartbeatManager manages automatic heartbeat sending for a sandbox
type heartbeatManager struct {
	jobGroupID string
	client     *plato.PlatoClient
	ctx        context.Context
	cancel     context.CancelFunc
	interval   time.Duration
	done       chan struct{}
}

// newHeartbeatManager creates and starts a heartbeat manager
func newHeartbeatManager(client *plato.PlatoClient, jobGroupID string, interval time.Duration) *heartbeatManager {
	ctx, cancel := context.WithCancel(context.Background())
	hm := &heartbeatManager{
		jobGroupID: jobGroupID,
		client:     client,
		ctx:        ctx,
		cancel:     cancel,
		interval:   interval,
		done:       make(chan struct{}),
	}
	go hm.run()
	return hm
}

func (hm *heartbeatManager) run() {
	defer close(hm.done)
	ticker := time.NewTicker(hm.interval)
	defer ticker.Stop()

	for {
		select {
		case <-hm.ctx.Done():
			return
		case <-ticker.C:
			// Send heartbeat
			_ = hm.client.Sandbox.SendHeartbeat(hm.ctx, hm.jobGroupID)
		}
	}
}

func (hm *heartbeatManager) stop() {
	hm.cancel()
	<-hm.done
}

// Helper functions to convert between C and Go types
func cString(s string) *C.char {
	return C.CString(s)
}

func goString(s *C.char) string {
	if s == nil {
		return ""
	}
	return C.GoString(s)
}

func freeCSandbox(cs *C.CSandbox) {
	if cs == nil {
		return
	}
	if cs.job_id != nil {
		C.free(unsafe.Pointer(cs.job_id))
	}
	if cs.public_id != nil {
		C.free(unsafe.Pointer(cs.public_id))
	}
	if cs.job_group_id != nil {
		C.free(unsafe.Pointer(cs.job_group_id))
	}
	if cs.url != nil {
		C.free(unsafe.Pointer(cs.url))
	}
	if cs.status != nil {
		C.free(unsafe.Pointer(cs.status))
	}
	if cs.correlation_id != nil {
		C.free(unsafe.Pointer(cs.correlation_id))
	}
}

func sandboxToC(s *models.Sandbox) *C.CSandbox {
	cs := (*C.CSandbox)(C.malloc(C.size_t(unsafe.Sizeof(C.CSandbox{}))))
	cs.job_id = cString(s.JobId)
	cs.public_id = cString(s.PublicId)
	cs.job_group_id = cString(s.JobGroupId)
	cs.url = cString(s.Url)
	cs.status = cString(s.Status)
	cs.correlation_id = cString(s.CorrelationId)
	return cs
}

// PlatoInit initializes a new Plato client and returns a client handle
//
//export PlatoInit
func PlatoInit(apiKey *C.char) C.int64_t {
	key := goString(apiKey)
	client := plato.NewClient(key)

	clientMux.Lock()
	defer clientMux.Unlock()

	id := nextID
	nextID++
	clients[id] = client

	return C.int64_t(id)
}

// PlatoFree releases a Plato client handle
//
//export PlatoFree
func PlatoFree(clientHandle C.int64_t) {
	clientMux.Lock()
	defer clientMux.Unlock()

	delete(clients, int64(clientHandle))
}

// PlatoSandboxCreate creates a new sandbox
// configJSON should be a JSON string of SimConfigDataset
// Returns a CSandbox pointer or NULL on error
//
//export PlatoSandboxCreate
func PlatoSandboxCreate(clientHandle C.int64_t, configJSON *C.char, dataset *C.char, alias *C.char, artifactID *C.char, service *C.char, errOut **C.CError) *C.CSandbox {
	clientMux.RLock()
	client, ok := clients[int64(clientHandle)]
	clientMux.RUnlock()

	if !ok {
		*errOut = makeError("invalid client handle", 1)
		return nil
	}

	// Parse config JSON using protojson
	config := &models.SimConfigDataset{}
	if err := protojson.Unmarshal([]byte(goString(configJSON)), config); err != nil {
		*errOut = makeError(fmt.Sprintf("failed to parse config: %v", err), 2)
		return nil
	}

	var artifactPtr *string
	if artifactID != nil {
		aid := goString(artifactID)
		artifactPtr = &aid
	}

	ctx := context.Background()
	sandbox, err := client.Sandbox.Create(
		ctx,
		config,
		goString(dataset),
		goString(alias),
		artifactPtr,
		goString(service),
	)

	if err != nil {
		*errOut = makeError(err.Error(), 3)
		return nil
	}

	*errOut = nil
	return sandboxToC(sandbox)
}

// PlatoSandboxSetup sets up a sandbox with SSH key
//
//export PlatoSandboxSetup
func PlatoSandboxSetup(clientHandle C.int64_t, jobID *C.char, configJSON *C.char, dataset *C.char, sshPublicKey *C.char, errOut **C.CError) *C.char {
	clientMux.RLock()
	client, ok := clients[int64(clientHandle)]
	clientMux.RUnlock()

	if !ok {
		*errOut = makeError("invalid client handle", 1)
		return nil
	}

	config := &models.SimConfigDataset{}
	if err := protojson.Unmarshal([]byte(goString(configJSON)), config); err != nil {
		*errOut = makeError(fmt.Sprintf("failed to parse config: %v", err), 2)
		return nil
	}

	ctx := context.Background()
	correlationID, err := client.Sandbox.SetupSandbox(
		ctx,
		goString(jobID),
		config,
		goString(dataset),
		goString(sshPublicKey),
	)

	if err != nil {
		*errOut = makeError(err.Error(), 3)
		return nil
	}

	*errOut = nil
	return cString(correlationID)
}

// PlatoSandboxMonitor monitors an operation via SSE and returns when complete
//
//export PlatoSandboxMonitor
func PlatoSandboxMonitor(clientHandle C.int64_t, correlationID *C.char, timeoutSeconds C.int, errOut **C.CError) {
	clientMux.RLock()
	client, ok := clients[int64(clientHandle)]
	clientMux.RUnlock()

	if !ok {
		*errOut = makeError("invalid client handle", 1)
		return
	}

	ctx := context.Background()
	timeout := time.Duration(int(timeoutSeconds)) * time.Second

	err := client.Sandbox.MonitorOperation(ctx, goString(correlationID), timeout)
	if err != nil {
		*errOut = makeError(err.Error(), 4)
		return
	}

	*errOut = nil
}

// PlatoSandboxStartHeartbeat starts automatic heartbeat for a sandbox
// interval is in seconds
//
//export PlatoSandboxStartHeartbeat
func PlatoSandboxStartHeartbeat(clientHandle C.int64_t, jobGroupID *C.char, intervalSeconds C.int, errOut **C.CError) {
	clientMux.RLock()
	client, ok := clients[int64(clientHandle)]
	clientMux.RUnlock()

	if !ok {
		*errOut = makeError("invalid client handle", 1)
		return
	}

	jgid := goString(jobGroupID)
	interval := time.Duration(int(intervalSeconds)) * time.Second

	hbMux.Lock()
	defer hbMux.Unlock()

	// Stop existing heartbeat if any
	if existing, ok := heartbeats[jgid]; ok {
		existing.stop()
	}

	// Start new heartbeat
	heartbeats[jgid] = newHeartbeatManager(client, jgid, interval)
	*errOut = nil
}

// PlatoSandboxStopHeartbeat stops automatic heartbeat for a sandbox
//
//export PlatoSandboxStopHeartbeat
func PlatoSandboxStopHeartbeat(jobGroupID *C.char) {
	jgid := goString(jobGroupID)

	hbMux.Lock()
	defer hbMux.Unlock()

	if hm, ok := heartbeats[jgid]; ok {
		hm.stop()
		delete(heartbeats, jgid)
	}
}

// PlatoSandboxSendHeartbeat sends a single heartbeat
//
//export PlatoSandboxSendHeartbeat
func PlatoSandboxSendHeartbeat(clientHandle C.int64_t, jobGroupID *C.char, errOut **C.CError) {
	clientMux.RLock()
	client, ok := clients[int64(clientHandle)]
	clientMux.RUnlock()

	if !ok {
		*errOut = makeError("invalid client handle", 1)
		return
	}

	ctx := context.Background()
	err := client.Sandbox.SendHeartbeat(ctx, goString(jobGroupID))
	if err != nil {
		*errOut = makeError(err.Error(), 5)
		return
	}

	*errOut = nil
}

// PlatoSandboxGet retrieves a sandbox by job ID
//
//export PlatoSandboxGet
func PlatoSandboxGet(clientHandle C.int64_t, jobID *C.char, errOut **C.CError) *C.CSandbox {
	clientMux.RLock()
	client, ok := clients[int64(clientHandle)]
	clientMux.RUnlock()

	if !ok {
		*errOut = makeError("invalid client handle", 1)
		return nil
	}

	ctx := context.Background()
	sandbox, err := client.Sandbox.Get(ctx, goString(jobID))
	if err != nil {
		*errOut = makeError(err.Error(), 6)
		return nil
	}

	*errOut = nil
	return sandboxToC(sandbox)
}

// PlatoSandboxDelete deletes a sandbox by job ID
//
//export PlatoSandboxDelete
func PlatoSandboxDelete(clientHandle C.int64_t, jobID *C.char, errOut **C.CError) {
	clientMux.RLock()
	client, ok := clients[int64(clientHandle)]
	clientMux.RUnlock()

	if !ok {
		*errOut = makeError("invalid client handle", 1)
		return
	}

	ctx := context.Background()
	err := client.Sandbox.Delete(ctx, goString(jobID))
	if err != nil {
		*errOut = makeError(err.Error(), 7)
		return
	}

	*errOut = nil
}

// PlatoSandboxDeleteVM deletes a VM by public ID
//
//export PlatoSandboxDeleteVM
func PlatoSandboxDeleteVM(clientHandle C.int64_t, publicID *C.char, errOut **C.CError) {
	clientMux.RLock()
	client, ok := clients[int64(clientHandle)]
	clientMux.RUnlock()

	if !ok {
		*errOut = makeError("invalid client handle", 1)
		return
	}

	ctx := context.Background()
	err := client.Sandbox.DeleteVM(ctx, goString(publicID))
	if err != nil {
		*errOut = makeError(err.Error(), 8)
		return
	}

	*errOut = nil
}

// PlatoFreeSandbox releases memory allocated for a CSandbox
//
//export PlatoFreeSandbox
func PlatoFreeSandbox(sandbox *C.CSandbox) {
	if sandbox != nil {
		freeCSandbox(sandbox)
		C.free(unsafe.Pointer(sandbox))
	}
}

// PlatoFreeString releases memory allocated for a C string
//
//export PlatoFreeString
func PlatoFreeString(s *C.char) {
	if s != nil {
		C.free(unsafe.Pointer(s))
	}
}

// PlatoFreeError releases memory allocated for a CError
//
//export PlatoFreeError
func PlatoFreeError(err *C.CError) {
	if err != nil {
		if err.error != nil {
			C.free(unsafe.Pointer(err.error))
		}
		C.free(unsafe.Pointer(err))
	}
}

func makeError(msg string, code int) *C.CError {
	err := (*C.CError)(C.malloc(C.size_t(unsafe.Sizeof(C.CError{}))))
	err.error = cString(msg)
	err.code = C.int(code)
	return err
}

func main() {
	// Required for buildmode=c-shared
	runtime.LockOSThread()
}
