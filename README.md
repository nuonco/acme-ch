# A.C.M.E. ClickHouse

### The Enterprise Standard for Managed ClickHouse Orchestration

Unlock the full potential of real-time analytics with **A.C.M.E. ClickHouse**. Our Bring Your Own Cloud (BYOC) model
empowers engineering teams to deploy managed ClickHouse clusters directly into their own AWS accounts, ensuring complete
data sovereignty and compliance.

<!-- [![Deploy to Nuon](https://nuon.co/Deploy.svg)](https://app.nuon.co/deploy?repository-url=https://github.com/fidiego/acme-ch) -->

### Architecture: Control Plane / Data Plane Separation

We leverage a sophisticated split-plane [architecture](docs/architecture-diagram.md) to deliver the best of managed
services and self-hosted control.

- **The Control Plane:** Hosted by A.C.M.E., this layer handles orchestration, updates, and monitoring logic. It never
  touches your data.
- **The Data Plane:** Resides entirely within _your_ cloud environment. Compute and storage resources are provisioned in
  your VPC, ensuring your data never leaves your security perimeter.

**Benefits:**

- **Zero Trust Security:** Your credentials and data stay with you.
- **Cost Transparency:** Pay AWS directly for infrastructure; pay us for management.
- **Regulatory Compliance:** Meet GDPR, HIPAA, and SOC2 requirements with ease by keeping data in-house.

**Core Capabilities:**

- **Infrastructure as Code:** GitOps-native deployment patterns.
- **Resilient Architecture:** Multi-Availability Zone fault tolerance.
- **Sovereign Data Control:** Isolated VPC deployment with strict access governance.

_Precision. Scale. Insight._

---

© 2025 A.C.M.E. Corporation.

---

Note: the purpose of this repository is to demonstrate how to integrate the Nuon API into a product to provide a
first-class experience.
