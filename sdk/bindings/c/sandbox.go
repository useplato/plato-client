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
	"time"
	"unsafe"

	plato "plato-sdk"
	"plato-sdk/models"
)

var clients = make(map[string]*plato.PlatoClient)
var nextID = 0

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

	return C.CString(string(result))
}

//export plato_delete_sandbox
func plato_delete_sandbox(clientID *C.char, publicID *C.char) *C.char {
	client, ok := clients[C.GoString(clientID)]
	if !ok {
		return C.CString(`{"error": "invalid client ID"}`)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

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

func main() {}
