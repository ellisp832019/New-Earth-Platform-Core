# Local AI Runtime Integration Boundary

New Earth Local AI Runtime is the local execution service for governed AI workloads. It is a Platform Core-declared service, not a Platform Core implementation detail.

## Owned By The Runtime

- local model execution;
- provider abstraction;
- deterministic routing;
- embeddings execution;
- runtime health and status;
- execution-side context and provenance;
- runtime impact advisories.

## Declared Public Interfaces

- `GET /health`
- `GET /v1/status`
- `GET /v1/models`
- `POST /v1/chat`
- `POST /v1/generate`
- `POST /v1/embeddings`
- `POST /v1/route/explain`
- `POST /v1/context/provenance`
- `GET /v1/impact/advisory`

## Consumption Boundary

Platform Core declares the contract. NEOS observes the implementation. GAIA consumes the execution service. Command Centre may surface status and availability. The runtime must not claim NEOS engineering authority or GAIA reasoning authority.
