module plato-bindings

go 1.25.3

require (
	google.golang.org/protobuf v1.36.10
	plato-sdk v0.0.0
)

require gopkg.in/yaml.v3 v3.0.1 // indirect

replace plato-sdk => ../..
