module plato-bindings

go 1.25.3

replace plato-sdk => ../../

require plato-sdk v0.0.0-00010101000000-000000000000

require (
	golang.org/x/crypto v0.43.0 // indirect
	golang.org/x/sys v0.37.0 // indirect
)
