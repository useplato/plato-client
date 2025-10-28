// Package stopwatch provides a simple stopwatch component.
package main

import (
	"fmt"
	"sync/atomic"
	"time"

	tea "github.com/charmbracelet/bubbletea"
)

var lastID int64

func nextID() int {
	return int(atomic.AddInt64(&lastID, 1))
}

// TickMsg is a message that is sent on every timer tick.
type TickMsg struct {
	// ID is the identifier of the stopwatch that sends the message. This makes
	// it possible to determine which stopwatch a tick belongs to when there
	// are multiple stopwatches running.
	//
	// Note, however, that a stopwatch will reject ticks from other
	// stopwatches, so it's safe to flow all TickMsgs through all stopwatches
	// and have them still behave appropriately.
	ID  int
	tag int
}

// StartStopMsg is sent when the stopwatch should start or stop.
type StartStopMsg struct {
	ID      int
	running bool
}

// ResetMsg is sent when the stopwatch should reset.
type ResetMsg struct {
	ID int
}

// Stopwatch model for the stopwatch component.
type Stopwatch struct {
	d       time.Duration
	id      int
	tag     int
	running bool

	// How long to wait before every tick. Defaults to 1 second.
	Interval time.Duration
}

// NewStopwatchWithInterval creates a new stopwatch with the given timeout and tick
// interval.
func NewStopwatchWithInterval(interval time.Duration) Stopwatch {
	return Stopwatch{
		Interval: interval,
		id:       nextID(),
	}
}

// NewStopwatch creates a new stopwatch with 10ms interval for smooth animation.
func NewStopwatch() Stopwatch {
	return NewStopwatchWithInterval(10 * time.Millisecond)
}

// ID returns the unique ID of the model.
func (m Stopwatch) ID() int {
	return m.id
}

// Init starts the stopwatch.
func (m Stopwatch) Init() tea.Cmd {
	return m.Start()
}

// Start starts the stopwatch.
func (m Stopwatch) Start() tea.Cmd {
	return tea.Batch(func() tea.Msg {
		return StartStopMsg{ID: m.id, running: true}
	}, tick(m.id, m.tag, m.Interval))
}

// Stop stops the stopwatch.
func (m Stopwatch) Stop() tea.Cmd {
	return func() tea.Msg {
		return StartStopMsg{ID: m.id, running: false}
	}
}

// Toggle stops the stopwatch if it is running and starts it if it is stopped.
func (m Stopwatch) Toggle() tea.Cmd {
	if m.Running() {
		return m.Stop()
	}
	return m.Start()
}

// Reset resets the stopwatch to 0.
func (m Stopwatch) Reset() tea.Cmd {
	return func() tea.Msg {
		return ResetMsg{ID: m.id}
	}
}

// Running returns true if the stopwatch is running or false if it is stopped.
func (m Stopwatch) Running() bool {
	return m.running
}

// Update handles the timer tick.
func (m Stopwatch) Update(msg tea.Msg) (Stopwatch, tea.Cmd) {
	switch msg := msg.(type) {
	case StartStopMsg:
		if msg.ID != m.id {
			return m, nil
		}
		m.running = msg.running
	case ResetMsg:
		if msg.ID != m.id {
			return m, nil
		}
		m.d = 0
	case TickMsg:
		if !m.running || msg.ID != m.id {
			break
		}

		// If a tag is set, and it's not the one we expect, reject the message.
		// This prevents the stopwatch from receiving too many messages and
		// thus ticking too fast.
		if msg.tag > 0 && msg.tag != m.tag {
			return m, nil
		}

		m.d += m.Interval
		m.tag++
		return m, tick(m.id, m.tag, m.Interval)
	}

	return m, nil
}

// Elapsed returns the time elapsed.
func (m Stopwatch) Elapsed() time.Duration {
	return m.d
}

// View of the timer component.
func (m Stopwatch) View() string {
	// Format as seconds with 1 decimal place
	seconds := m.d.Seconds()

	// If less than 1 minute, show seconds with 1 decimal
	if seconds < 60 {
		return fmt.Sprintf("%.1fs", seconds)
	}

	// If 1 minute or more, show minutes and seconds
	minutes := int(seconds / 60)
	remainingSeconds := seconds - float64(minutes*60)
	return fmt.Sprintf("%dm %.1fs", minutes, remainingSeconds)
}

func tick(id int, tag int, d time.Duration) tea.Cmd {
	return tea.Tick(d, func(_ time.Time) tea.Msg {
		return TickMsg{ID: id, tag: tag}
	})
}
