# Changelog

All notable changes to the **AegisMesh IDE Sentinel** extension will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-10-03

### Added
- **Core Extension Foundation:** Initial release of the AegisMesh IDE Sentinel security adapter for Visual Studio Code.
- **Runtime Health Monitoring:** Interactive and background connectivity checks against the AegisMesh Runtime Integrity Core (`GET /health`) with live status bar indicators.
- **Policy Enforcement Interceptor:** `aegismesh.testAction` command enabling developers to submit candidate tool calls (`shell.exec`, `file.read`, `web.search`, etc.) to the PEP (`POST /enforce`) and evaluate policy decisions in real time.
- **Multi-State Decision Handling:** First-class visual feedback and detailed modal inspections for `ALLOW`, `BLOCK`, `APPROVAL`, and `QUARANTINE` enforcement verdicts.
- **Mission Execution & Streaming:** `aegismesh.runMission` command enabling multi-agent coordination dispatch with live log streaming to a dedicated `AegisMesh Sentinel` output channel.
- **Dynamic Configuration:** Configurable backend Core URL (`aegismesh.backendUrl`) and agent identifier (`aegismesh.agentId`) with auto-reconnect listeners.
- **Cryptographic Audit Linking:** Transparent surface of backend `event_id` and audit references on every action decision.
