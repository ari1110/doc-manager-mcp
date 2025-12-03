// Test fixture: Go struct with yaml/json tags.
package config

type AppConfig struct {
	Name        string `yaml:"name" json:"name"`
	Version     string `yaml:"version,omitempty" json:"version,omitempty"`
	Debug       bool   `yaml:"debug" json:"debug"`
	MaxRetries  int    `yaml:"max_retries" json:"maxRetries"`
	Timeout     int    `yaml:"timeout,omitempty" json:"timeout,omitempty"`
}

type DatabaseSettings struct {
	Host     string `yaml:"host" json:"host"`
	Port     int    `yaml:"port" json:"port"`
	Database string `yaml:"database" json:"database"`
}
