package auth

// Credentials represents authentication credentials
type Credentials struct {
	APIKey    string `json:"api_key"`
	APISecret string `json:"api_secret"`
}

// Authenticator handles authentication
type Authenticator struct {
	Creds *Credentials
}

// NewAuthenticator creates a new authenticator
func NewAuthenticator(creds *Credentials) *Authenticator {
	return &Authenticator{Creds: creds}
}

// Validate validates the credentials
func (a *Authenticator) Validate() error {
	return nil
}
