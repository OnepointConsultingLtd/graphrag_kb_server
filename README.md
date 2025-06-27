# GraphRag Knowledge Base Engine

Project with support for multi tennant indexing and search functions to create the knowledge graphs and the embeddings that can be used for [GraphRAG](https://github.com/microsoft/graphrag) and [LightRAG](https://github.com/HKUDS/LightRAG).
It also provides a simple API to expose [GraphRAG](https://github.com/microsoft/graphrag) and [LightRAG](https://github.com/HKUDS/LightRAG) as an API.

The tennant API has three main methods:

- Upload a zip file with the knowledge base
- Perform local, global and drift queries on an existing knowledge base
- Retrieve the GraphRAG context based on a question
- Delete a specific index or project

# Install

In the project folder execute:

```ps1
uv venv
# Under Windows
.venv\Scripts\activate
uv sync
```

```bash
uv venv
# Under Linux
source .venv/bin/activate
uv sync
```

# Configuration

The application is configured used environment variables which you can set in a `.env` file.

And example with all variables can be found here:

[.env_local](.env_local)

The most important variables are:

```
# The Open API Key. See https://platform.openai.com/
OPENAI_API_KEY=<key>

# The model for GraphRAG. For now only OpenAI models
OPENAI_API_MODEL=gpt-4o-mini
OPENAI_API_MODEL_EMBEDDING=text-embedding-3-small

# The key for Gemini. This works with LightRAG
GEMINI_API_KEY=<key>

# The LightRAG Model
# Supported models gpt-4o-mini, gpt-4o, gemini-2.0-flash
LIGHTRAG_MODEL=gpt-4o-mini
# LIGHTRAG_MODEL=gpt-4o-mini

# The configuration directory. Here you can find the administration.yaml file which has the administrators JWT email addresses.
CONFIG_DIR=/development/onepoint/thinqwin/graphrag_kb_server/config

# The directory for uploaded files.
UPLOAD_DIR=/mnt/graphrag/upload

# The directory for the tenant data.
GRAPHRAG_ROOT_DIR=/mnt/graphrag/tennants/

# For GraphRAG the dtabase directory
VECTOR_DB_DIR=output/lancedb

# For GraphRAG the verbose mode
INDEX_VERBOSE=false

# The maximum number of tokens for the local context (GraphRAG)
LOCAL_CONTEXT_MAX_TOKENS = 20000

# The maximum number of tokens for the global context (GraphRAG)
GLOBAL_CONTEXT_MAX_TOKENS = 20000

# Whether claims are enabled (GraphRAG)
CLAIMS_ENABLED=false

# The websocket server (GraphRAG)
SERVER=0.0.0.0

# The websocket port (GraphRAG)
PORT=9999

# The JWT secret algorithm
JWT_ALGORITHM=HS512

# The JWT time delta in minutes
JWT_TIME_DELTA_MINUTES=120

# The JWT generation folder
JWT_GEN_FOLDER=/tmp/data_wellness/jwt_gen

# This needs to be generated. See README for instructions.
ADMIN_JWT=<jwt>
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

Before running this command make sure that the .env is available and the CONFIG_DIR environment variable points to the config folder.

This is the command that allows to generate the administration token:

```bash
# Under Windows
# .venv\Scripts\activate
source .venv/bin/activate
python ./graphrag_kb_server/cli/jwt_main.py "<name>" "<email>"
```

This will produce a file admin_token.md with the token.

The administration token should be also inserted into the .env file (ADMIN_JWT variable)

# Running the server

Before running the server, build the front end first. See the instructions below.

```bash
python ./graphrag_kb_server/main/webapp.py
```

## Swagger UI

Please open to see the exposed API and its parameters:

http://127.0.0.1:9999/docs

Here is a brief screenshot of the methods in the Swagger API:

![Description of the image](./docs/screenshots/kb_server.png)

## Install the server as a service in Linux

You can use the file graph_kb_server_sample.service as a template for installing a service in Linux using systemd.

The installation commands are typically:

```bash
sudo cp *.service /etc/systemd/system/
sudo systemctl enable graphrag_kb_server.service
sudo systemctl start graphrag_kb_server.service
sudo systemctl status graphrag_kb_server.service
```

## Building the front end

You will need node version 20 or later for this.

You can build the front-end using this command:

```ps1
# Under Windows
.venv\Scripts\activate
uv run ./graphrag_kb_server/cli/build_web.py
```

```bash
# Under Linux
source .venv/bin/activate
uv run ./graphrag_kb_server/cli/build_web.py
```

Alternatively you can build the UI by running these commands:

```bash
cd front_end
yarn
yarn run build

cd ..
cd front_end_chat
yarn
yarn run build
```

You can also use npm instead of yarn.

Also change the file [front_end/server.js](front_end/server.js) so that the UI is linked to your server domain.

So change:

```js
export const BASE_SERVER = "http://localhost:9999"
```

to 

```js
export const BASE_SERVER = "https://yourdomain.com"
```

## Starting the front end

To start the front end for graph visualisation in development mode:

```bash
cd front_end
yarn dev
```

To start the front end for the chat application in development mode:

```bash
cd front_end_chat
yarn dev
```

Make sure to start the server with the command below.

You can access it via: http://localhost:1234/index

To start the front end in production mode in the root folder of the project:

```bash
uv run ./graphrag_kb_server/main/webapp.py
```

You can access it via: http://localhost:9999/index

# Docker

## Build

You can build the image with the scripts `docker_build.ps1` or `docker_build.sh`.

## Run Docker

When you start the container, please define these variables:

```
ADMIN_TOKEN_NAME
ADMIN_TOKEN_EMAIL
OPENAI_API_KEY
GEMINI_API_KEY
SERVER_BASE_URL
```

ADMIN_TOKEN_NAME can be your name
ADMIN_TOKEN_EMAIL can be your email

SERVER_BASE_URL is used for snippet generation and should be your domain, ie. something like e.g. http(s)://<domain>(:<port>)

As well as the volume for this path:

```
/var/graphrag
```

You will need to map a port to 9999.

We have published a Docker image on Docker Hub that you can use: gilf/graphrag_kb_server







