# Platform Intention
This project is intended to showcase a Containerised Data Platform. The design is intended to be free to spin up locally so anyone can run it, but scalable to cloud infrastructure and cloud agnostic.

## Users:
* **Data Automation**: users of the platform want data that is up to date, validated, and enhanced. Data transformations and orchestration with prefect is completed in `backend/` 
* **API Users**: users of the platform want public access to the data, but the platform must control what users can and cant interact with. A FastAPI application in `api/` provides a public endpoint for data that is explicitly for public use.
* **Data Analysts**: users of the platform may want to explore the available data without downloading it. `frontend/` contains marimo notebooks and tools that allow users to analyse the data interactively, in their browser. 

## Use Case
Climate data is loaded into a data lake and transformed to enable health-driven analytics. 

# 💻 Local Environment Prerequisites

To run the whole platform the host machine must satisfy the following system requirements:

1. **Git**: Git must be installed on your host machine.
2. **Docker Engine**: Docker must be installed and running on your host machine.
3. **Execution**:
```shell
git clone https://github.com/neilmolky/environmental-health-platform
cd environmental-health-platform 
docker compose up
```
4. **Useage**: with the services deployed, you should be able to access 4 endpoints in your browser. Ensure no other services are running on these ports.
    - localhost:8000 -> The api analysts would use to get data or manually trigger pipelines.
    - localhost:8001 -> The fake api mock service mirrors.
    - localhost:4200 -> The prefect server orchestrating data pipelines
    - localhost:2718 -> The marimo interactive analysis platform

*See also: CONTRIBUTING.md explains how to set up a dev-container if you want to add features and test them locally*


# System Design
The system exposes 4 ports as services. 

```mermaid
graph TD;
    %% --- ZERO TRUST STACKS ---
    subgraph Storage-Backend ["🔒 Storage Workspace (blob-access Network)"]
        direction LR
        bronze[(🥉 Bronze Layer)] --> silver[(🥈 Silver Layer)] --> gold[(🥇 Gold Layer)]
    end

    subgraph Core-Mesh ["🌐 Service Control Mesh (platform-mesh Network)"]
        direction TB
        
        subgraph backend-service ["🛠️ Backend Dev / Worker"]
            data-pipeline[Prefect Pipelines & Sensors]
            storage-client-back[Abstract Storage Interface]
            data-pipeline <--> storage-client-back
        end

        subgraph api-service ["⚡ FastAPI Analytics Gateway"]
            get-data[GET /api/v1/metrics]
            trigger-pipeline[POST /api/v1/trigger-ingestion]
            storage-client-api[Abstract Storage Interface]
            get-data <--> storage-client-api
        end

        subgraph orchestration ["🎛️ Orchestration Center"]
            prefect-server[Prefect 3.x Server]
        end

        subgraph mock ["🧪 Test Simulator Space"]
            met-office-mock[Met Office API Simulator]
        end

        subgraph frontend-service ["📊 Presentation & Analytical Space"]
            marimo-notebook[Marimo Analytics Dashboard]
        end
    end

    %% --- INTER-CONTAINER NETWORKING & DATA PIPELINES ---
    storage-client-back <==> Storage-Backend
    storage-client-api <==> gold

    trigger-pipeline ==> |HTTP Control Signal| prefect-server
    prefect-server <==> |Pipeline State Synch| data-pipeline
    data-pipeline -.-> |HTTP Ingestion Request| met-office-mock
    marimo-notebook ==> |REST Data Queries| get-data

    %% --- EXPOSED USER PORTS ---
    user((🧑‍💻 Data Analyst / Engineer)) <-- port:8000 --> api-service
    user <-- port:2718 --> marimo-notebook
    user <-- port:4200 --> prefect-server
    user <-- port:8001 --> mock

    %% --- VISUAL REFINEMENTS ---
    style Storage-Backend fill:#f9f,stroke:#333,stroke-width:2px
    style Core-Mesh fill:#bbf,stroke:#333,stroke-width:1px
    style user fill:#fff,stroke:#333,stroke-width:2px

```
