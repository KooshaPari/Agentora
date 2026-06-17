package adapters

import "fmt"

// adapters maps registry names to their adapter implementations.
var adapters = map[Registry]RegistryAdapter{
	RegistryNPM:    &NpmAdapter{},
	RegistryPyPI:   &PyPIAdapter{},
	RegistryCrates: &CratesAdapter{},
	RegistryGo:     &GoProxyAdapter{},
	RegistryHex:    &HexAdapter{},
	RegistryZig:    &ZigAdapter{},
	RegistryMojo:   &MojoAdapter{},
}

// GetAdapter returns the adapter for the given registry.
func GetAdapter(registry Registry) (RegistryAdapter, error) {
	a, ok := adapters[registry]
	if !ok {
		return nil, fmt.Errorf("no adapter for registry: %s", registry)
	}
	return a, nil
}

// AllAdapters returns all registered adapters.
func AllAdapters() map[Registry]RegistryAdapter {
	return adapters
}
