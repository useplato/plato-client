package main

import (
	"github.com/charmbracelet/bubbles/key"
	"github.com/charmbracelet/bubbles/list"
	tea "github.com/charmbracelet/bubbletea"
)

type MainMenuModel struct {
	choices list.Model
}

type menuItem struct {
	title       string
	description string
}

func (i menuItem) Title() string       { return i.title }
func (i menuItem) Description() string { return i.description }
func (i menuItem) FilterValue() string { return i.title }

func NewMainMenuModel() MainMenuModel {
	items := []list.Item{
		menuItem{title: "Launch Environment", description: "Start from an existing environment or a blank slate."},
		menuItem{title: "Configuration", description: "View API key and settings"},
		menuItem{title: "Quit", description: "Exit the CLI"},
	}

	l := list.New(items, list.NewDefaultDelegate(), 80, 15)
	l.Title = "Main Menu"
	l.SetShowStatusBar(false)
	l.SetFilteringEnabled(false)

	return MainMenuModel{
		choices: l,
	}
}

func (m MainMenuModel) Init() tea.Cmd {
	return nil
}

func (m MainMenuModel) Update(msg tea.Msg) (MainMenuModel, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		h := 15 // Fixed reasonable height for menu items
		m.choices.SetSize(msg.Width, h)
		return m, nil
	case tea.KeyMsg:
		switch {
		case key.Matches(msg, key.NewBinding(key.WithKeys("enter"))):
			// Handle selection
			selectedItem := m.choices.SelectedItem()
			if selectedItem != nil {
				item := selectedItem.(menuItem)
				switch item.title {
				case "Launch Environment":
					return m, func() tea.Msg {
						return NavigateMsg{view: ViewLaunchEnvironment}
					}
				case "Configuration":
					return m, func() tea.Msg {
						return NavigateMsg{view: ViewConfig}
					}
				case "Exit":
					return m, tea.Quit
				}
			}
			return m, nil
		}
	}

	var cmd tea.Cmd
	m.choices, cmd = m.choices.Update(msg)
	return m, cmd
}

func (m MainMenuModel) View() string {
	return RenderHeader() + "\n" + m.choices.View()
}
