
# Qsmith Authentication & Authorization Plan
## Keycloak Integration + Local Auth Toggle

Version: 1.0  
Target: Codex implementation  
Language: Python backend  
Deployment: containerized  
Configuration: `.env`

---

# 1. Technical Overview

Qsmith is a testing support tool that executes suites composed of tests and operations interacting with external systems (queues, APIs, mock servers).

The platform requires authentication and role-based authorization.

The chosen identity provider is **Keycloak**, which provides:

- Single Sign-On
- OpenID Connect authentication
- Role management
- JWT token issuance

Keycloak supports OpenID Connect on top of OAuth2 and is commonly used to provide identity and access management for modern applications. :contentReference[oaicite:1]{index=1}

Authentication will use the **OIDC Authorization Code Flow**, which works as follows:

1. User accesses Qsmith.
2. Qsmith redirects to Keycloak login.
3. User authenticates.
4. Keycloak redirects back with an authorization code.
5. Qsmith exchanges the code for tokens.
6. Qsmith validates the token and extracts user information.

This flow is recommended for web applications because it securely returns ID, access and refresh tokens after authentication. :contentReference[oaicite:2]{index=2}

---

# 2. Design Goals

The authentication system must:

- integrate with corporate Keycloak
- allow **local development without Keycloak**
- support **user roles**
- enforce **authorization rules**
- keep configuration outside code
- work consistently across environments

Key principles:

- Authentication provider must be configurable
- Authorization must always remain active
- Local development must not require external infrastructure
- Security configuration must live in `.env`

---

# 3. Authentication Modes

The system supports two authentication modes.

## 3.1 Keycloak mode

Used in:

- dev
- test
- production

Characteristics:

- login redirect to Keycloak
- token validation
- roles extracted from token
- user synchronized with local database

## 3.2 Local mode

Used in:

- local development

Characteristics:

- no external authentication
- a default user is created automatically
- role is configured in `.env`

Authorization still applies.

---

# 4. Environment Configuration

All configuration must come from environment variables.

Create:

```

.env
.env.example

```

## Example `.env`

```

APP_ENV=local
APP_PORT=8080

KEYCLOAK_ENABLED=false

AUTH_DEFAULT_ROLE=ADMIN
AUTH_DEFAULT_USERNAME=local.admin
AUTH_DEFAULT_EMAIL=[local.admin@qsmith.local](mailto:local.admin@qsmith.local)

KEYCLOAK_SERVER_URL=[https://keycloak.company.it](https://keycloak.company.it)
KEYCLOAK_REALM=company
KEYCLOAK_CLIENT_ID=qsmith
KEYCLOAK_CLIENT_SECRET=change-me

KEYCLOAK_REDIRECT_URI=[http://localhost:8080/auth/callback](http://localhost:8080/auth/callback)
KEYCLOAK_POST_LOGOUT_REDIRECT_URI=[http://localhost:8080/](http://localhost:8080/)

KEYCLOAK_VERIFY_SSL=true

```

---

# 5. Configuration Loader

Create module:

```

qsmith/config.py

````

Responsibilities:

- read environment variables
- convert types
- expose configuration object

Example structure:

```python
from dataclasses import dataclass
import os


def as_bool(v, default=False):
    if v is None:
        return default
    return v.lower() in ["true", "1", "yes", "on"]


@dataclass
class Settings:
    app_env: str
    keycloak_enabled: bool

    auth_default_role: str
    auth_default_username: str
    auth_default_email: str

    keycloak_server_url: str
    keycloak_realm: str
    keycloak_client_id: str
    keycloak_client_secret: str

    keycloak_redirect_uri: str
    keycloak_post_logout_redirect_uri: str
    keycloak_verify_ssl: bool


def load_settings():
    return Settings(
        app_env=os.getenv("APP_ENV", "local"),
        keycloak_enabled=as_bool(os.getenv("KEYCLOAK_ENABLED"), False),

        auth_default_role=os.getenv("AUTH_DEFAULT_ROLE", "ADMIN"),
        auth_default_username=os.getenv("AUTH_DEFAULT_USERNAME", "local.admin"),
        auth_default_email=os.getenv("AUTH_DEFAULT_EMAIL", "local.admin@qsmith.local"),

        keycloak_server_url=os.getenv("KEYCLOAK_SERVER_URL", ""),
        keycloak_realm=os.getenv("KEYCLOAK_REALM", ""),
        keycloak_client_id=os.getenv("KEYCLOAK_CLIENT_ID", ""),
        keycloak_client_secret=os.getenv("KEYCLOAK_CLIENT_SECRET", ""),

        keycloak_redirect_uri=os.getenv("KEYCLOAK_REDIRECT_URI", ""),
        keycloak_post_logout_redirect_uri=os.getenv("KEYCLOAK_POST_LOGOUT_REDIRECT_URI", ""),
        keycloak_verify_ssl=as_bool(os.getenv("KEYCLOAK_VERIFY_SSL"), True),
    )
````

---

# 6. Auth Provider Abstraction

Authentication must be abstracted.

Create interface:

```
qsmith/auth/provider.py
```

```
class AuthProvider:

    def get_current_user(self, request):
        raise NotImplementedError()

    def login(self, request):
        raise NotImplementedError()

    def logout(self, request):
        raise NotImplementedError()
```

---

# 7. Providers Implementation

Two providers must exist.

## 7.1 KeycloakAuthProvider

Location:

```
qsmith/auth/keycloak_provider.py
```

Responsibilities:

* redirect login
* exchange authorization code
* validate JWT
* extract claims
* synchronize user
* logout

User claims to extract:

```
sub
preferred_username
email
given_name
family_name
roles
```

---

## 7.2 LocalAuthProvider

Location:

```
qsmith/auth/local_provider.py
```

Responsibilities:

* generate local user
* assign role from environment

Example:

```python
class LocalAuthProvider(AuthProvider):

    def __init__(self, settings):
        self.settings = settings

    def get_current_user(self, request):
        return CurrentUser(
            username=self.settings.auth_default_username,
            email=self.settings.auth_default_email,
            role=self.settings.auth_default_role,
            auth_source="local"
        )
```

---

# 8. Provider Factory

Create factory:

```
qsmith/auth/factory.py
```

```
def build_auth_provider(settings):

    if settings.keycloak_enabled:
        return KeycloakAuthProvider(settings)

    return LocalAuthProvider(settings)
```

This prevents `if keycloak_enabled` checks scattered in the code.

---

# 9. Current User Model

All authentication providers must return the same user model.

```
qsmith/auth/models.py
```

```
from dataclasses import dataclass

@dataclass
class CurrentUser:

    username: str
    email: str
    role: str

    auth_source: str = "keycloak"
```

---

# 10. User Persistence

Create database table:

```
users
```

Example schema:

```
id UUID
keycloak_user_id VARCHAR
username VARCHAR
email VARCHAR
first_name VARCHAR
last_name VARCHAR
role VARCHAR
is_active BOOLEAN
created_at TIMESTAMP
updated_at TIMESTAMP
```

User provisioning happens at first login.

---

# 11. Role Model

Initial roles:

```
ADMIN
CONSULTANT
TESTER
```

Roles originate from:

```
Keycloak client roles
```

Example token structure:

```
resource_access:
  qsmith:
    roles:
      - admin
```

Mapping:

```
admin -> ADMIN
consultant -> CONSULTANT
tester -> TESTER
```

---

# 12. Authorization Model

Authorization is implemented in application code.

Create module:

```
qsmith/authorization/permissions.py
```

Example:

```
ADMIN -> full access
CONSULTANT -> configuration + read
TESTER -> operational usage
```

Example matrix:

```
ADMIN
  suites: WRITE
  mocks: WRITE
  queues: WRITE
  users: WRITE

CONSULTANT
  suites: WRITE
  mocks: WRITE
  queues: WRITE
  users: READ

TESTER
  suites: WRITE
  mocks: READ
  queues: READ
  users: NO_ACCESS
```

---

# 13. Permission Guard

Create decorators:

```
qsmith/authorization/guards.py
```

Example:

```
@require_access("users", READ)
def list_users():
```

Authorization must be enforced server-side.

UI must respect the same rules.

---

# 14. Authentication Middleware

Create middleware:

```
qsmith/auth/middleware.py
```

Responsibilities:

* resolve current user
* attach user to request

```
request.current_user
```

---

# 15. Startup Validation

Add validation:

```
if APP_ENV == "prod" and KEYCLOAK_ENABLED == false
    raise startup error
```

This prevents insecure deployments.

---

# 16. File Structure

```
qsmith/

  config.py

  auth/
      provider.py
      factory.py
      keycloak_provider.py
      local_provider.py
      models.py
      middleware.py

  authorization/
      permissions.py
      guards.py

  identity/
      models.py
      repository.py
      service.py
```

---

# 17. Implementation Checklist

## configuration

[ ] create `.env.example`
[ ] implement config loader
[ ] support `KEYCLOAK_ENABLED` toggle

## authentication

[ ] implement auth provider interface
[ ] implement Keycloak provider
[ ] implement local provider
[ ] implement provider factory
[ ] implement middleware

## users

[ ] create users table
[ ] implement user provisioning
[ ] sync claims from token

## authorization

[ ] implement role matrix
[ ] implement permission guards

## security

[ ] validate JWT tokens
[ ] implement logout flow
[ ] enforce production validation

---

# 18. Future Extensions

Potential improvements:

* fine-grained permissions
* workspace level access
* team based authorization
* Keycloak admin API integration
* Keycloak Authorization Services

---

# End of Plan
