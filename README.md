# ```accountmanager```

## Application Install

### Prerequisites

1. [Google Chrome](https://www.google.com/chrome/) - Initial Token Auth workflow
2. [Python 3.8 - 3.11](https://www.python.org/) - To run the script
3. [Google API Service Account Key](https://pygsheets.readthedocs.io/en/stable/authorization.html) - to access Google sheets.
4. [Poetry](https://python-poetry.org/) - To build the code locally (optional)

### Installation

```bash
pip install https://github.com/pattertj/accountmanager/releases/download/v2.0.0/accountmanager-2.0.0-py3-none-any.whl
```

### Troubleshooting

1. ```accountmanager --help``` will list the available command options.
2. The first time accessing TDA will require some credentials, it can be a bit slow the first time. These are stored in your local keychain. After that, the json token is stored locally to the project.
3. I found that I needed to update by Google API token by wrapping it in a {"web": {ORIGINAL TOKEN} } wrapper. See below for an example.

```json
{ "web" :
    {
        "type": "service_account",
        "project_id": "proj id",
        "private_key_id": "SECRETS",
        "private_key": "SECRET_STUFF",
        "client_email": "SECRET",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "SECRETS"
    }
}
```

## Development Setup

### Pull and Install

```bash
git clone https://github.com/pattertj/accountmanager.git
```

```bash
poetry install
```

### Setup Pre-Commit Hooks

```bash
poetry run pre-commit install -t pre-commit
poetry run pre-commit install -t pre-push
```

 you ever need to skip these hooks you can run git commit --no-verify or git push --no-verify
