// Package main provides debug logging utilities for the Plato CLI.
//
// This file implements a debug logger that writes log messages to
// ~/.plato/debug.log for troubleshooting CLI operations and tracking events.
package main

import (
	"fmt"
	"log"
	"os"
	"path/filepath"
)

var debugLogger *log.Logger

func initLogger() error {
	logDir := filepath.Join(os.Getenv("HOME"), ".plato")
	if err := os.MkdirAll(logDir, 0755); err != nil {
		return err
	}

	logFile := filepath.Join(logDir, "debug.log")
	file, err := os.OpenFile(logFile, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
	if err != nil {
		return err
	}

	debugLogger = log.New(file, "", log.LstdFlags|log.Lshortfile)
	debugLogger.Printf("=== Plato CLI Started ===")
	return nil
}

func logDebug(format string, args ...interface{}) {
	if debugLogger != nil {
		debugLogger.Output(2, fmt.Sprintf(format, args...))
	}
}
