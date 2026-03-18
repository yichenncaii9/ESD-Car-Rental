---
name: lab_port_mappings
description: ESD lab docker port remapping strategy to avoid conflicts with local k8s project cluster
type: project
---

Lab services are remapped to 8xxx host ports to avoid conflicts with the local Kubernetes project cluster (which uses 5xxx ports internally).

**Why:** Local k8s cluster (Minikube) already occupies the 5xxx range. Port 6000 is blocked by browsers (X11), port 7000 is used by macOS Control Center.

**How to apply:** Always use 8xxx ports for ESD lab docker services. Never revert to 5xxx host ports for labs.

## Port Map

| Service | Host Port | Container Port | Compose file |
|---|---|---|---|
| book | 8010 | 5000 | `W10 Book-cointainer lab-resources/compose.yaml` |
| order | 8011 | 5001 | `W10 Book-cointainer lab-resources/compose.yaml` |
| shipping_record | 8012 | 5002 | `W10 Book-cointainer lab-resources/compose.yaml` |
| place_order | 8100 | 5100 | `W10 Book-cointainer lab-resources/compose.yaml` |
| RabbitMQ AMQP | 8672 | 5672 | `5. Create Place Order composite service/lab-resources/rabbitmq/compose.yaml` |
| RabbitMQ UI | 18672 | 15672 | `5. Create Place Order composite service/lab-resources/rabbitmq/compose.yaml` |

> Note: RabbitMQ was remapped to 6672/16672 in the session — consider updating to 8672/18672 for consistency.

## Lab Directories
- Main lab: `/Applications/MAMP/htdocs/y2s2/ESD/W10 Book-cointainer lab-resources/`
- RabbitMQ: `/Applications/MAMP/htdocs/y2s2/ESD/5. Create Place Order composite service/lab-resources/rabbitmq/`
- Project root: `/Applications/MAMP/htdocs/y2s2/ESD/`
