# GraphRag Knowledge Base Engine

Project with support for multi tennant indexing and search functions to create the knowledge graphs and the embeddings that can be used for GraphRAG.
It also provides a simple API to expose GraphRAG as an API.

The tennant API has three main methods:

- Upload a zip file with the knowledge base
- Perform local, global and drift queries on an existing knowledge base
- Retrieve the GraphRAG context based on a question
- Delete a specific index or project

# Install

```bash
# conda remove -n graphrag_kb_server --all
conda create -n graphrag_kb_server python=3.12
conda activate graphrag_kb_server
pip install poetry
poetry install
pip install aiohttp_swagger3
```

# Configuration

The application is configured used environment variables which you can set in a `.env` file.

And example with all variables can be found here:

[.env_local](.env_local)

The most important variables are:

```
# The Open API key
OPENAI_API_KEY

# The directory with the text files with the knowledge base.
DOCS_DIR

# The directory where the whole GraphRAG files are stored after generation
GRAPHRAG_ROOT_DIR

# The director where the vectors are stored
STORAGE_BASE_DIR

# Whether claims are turned on or not
CLAIMS_ENABLED=false
```

# How the system works

This is a Knowledge Base service which supports multiple tennants with multiple projects each. You have two roles:

- Administrators: administrators can manage tennants
- Tennants: tennants can manage projects

A tennant will create a project when he/she uploads a file that is indexed. After the project has been created the tennant can query it or use its extracted context.

The whole authentication system is based on tokens. The administrator will have his/her own token as well as the tennant.

In order to promote a user to an administrator you will to create a token for the administrator (see next chapter) and then you need to add his / her email to the file:

[./config/administration.yaml](./config/administration.yaml)

An example of this file can be found here:

[./config/administration_local.yaml](./config/administration_local.yaml)

# Creating the administration token

In order to create tennants via the API you will need to create an administration token first. The administrator is the one who can create tennants and therefore needs a token.

This is the command that allows to generate the administration token:

```bash
conda activate graphrag_kb_server
python ./graphrag_kb_server/cli/jwt_main.py "<name>" "<email>"
```

This will produce a file admin_token.md with the token.

# Running the server

```bash
poetry run python ./graphrag_kb_server/main/webapp.py
```

## Swagger UI

Please open to see the exposed API and its parameters:

http://127.0.0.1:9999/docs

Here is a brief screenshot of the methods in the Swagger API:

![Description of the image](./docs/screenshots/kb_server.png)




